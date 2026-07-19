from datetime import UTC, datetime
from uuid import UUID

import jwt

from app.core.errors import ConflictError, UnauthorizedError
from app.core.security import create_access_token, create_refresh_token, decode_token
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.repositories.user_repository import UserRepository
from app.schemas.auth_schemas import LoginSchema, RegisterSchema, TokenResponse
from app.services.security import hash_password, verify_password


class AuthService:
    def __init__(
        self,
        user_repository: UserRepository,
        refresh_token_repository: RefreshTokenRepository,
    ):
        self.user_repository = user_repository
        self.refresh_token_repository = refresh_token_repository

    async def _issue_tokens(self, user: User) -> TokenResponse:
        access_token = create_access_token(user.id, user.is_admin)
        refresh_token, jti, expires_at = create_refresh_token(user.id)
        await self.refresh_token_repository.create(
            RefreshToken(user_id=user.id, jti=jti, expires_at=expires_at)
        )
        return TokenResponse(access_token=access_token, refresh_token=refresh_token)

    async def register(self, data: RegisterSchema) -> tuple[User, TokenResponse]:
        if await self.user_repository.get_by_email(data.email):
            raise ConflictError("Email already registered")
        if await self.user_repository.get_by_username(data.username):
            raise ConflictError("Username already taken")

        user = User(
            email=data.email,
            username=data.username,
            password_hash=hash_password(data.password),
            display_name=data.display_name,
        )
        user = await self.user_repository.create(user)
        tokens = await self._issue_tokens(user)
        return user, tokens

    async def login(self, data: LoginSchema) -> tuple[User, TokenResponse]:
        user = await self.user_repository.get_by_email(data.email)
        if (
            not user
            or not user.password_hash
            or not verify_password(data.password, user.password_hash)
        ):
            raise UnauthorizedError("Invalid credentials")

        tokens = await self._issue_tokens(user)
        return user, tokens

    async def refresh(self, refresh_token: str) -> TokenResponse:
        jti = self._decode_jti(refresh_token, "Invalid refresh token")

        stored = await self.refresh_token_repository.get_by_jti(jti)
        if not stored or stored.revoked_at is not None:
            raise UnauthorizedError("Refresh token revoked")
        if stored.expires_at <= datetime.now(UTC):
            raise UnauthorizedError("Refresh token expired")

        user = await self.user_repository.get_by_id(stored.user_id)
        if not user:
            raise UnauthorizedError("User not found")

        await self.refresh_token_repository.revoke(jti)
        return await self._issue_tokens(user)

    async def logout(self, refresh_token: str) -> None:
        jti = self._decode_jti(refresh_token, "Invalid refresh token")
        await self.refresh_token_repository.revoke(jti)

    async def get_current_user(self, access_token: str) -> User:
        try:
            payload = decode_token(access_token)
            user_id = UUID(payload["sub"])
        except (jwt.PyJWTError, KeyError, ValueError) as exc:
            raise UnauthorizedError("Invalid access token") from exc

        user = await self.user_repository.get_by_id(user_id)
        if not user or not user.is_active:
            raise UnauthorizedError("User not found or inactive")
        return user

    @staticmethod
    def _decode_jti(token: str, invalid_message: str) -> str:
        try:
            payload = decode_token(token)
            return payload["jti"]
        except (jwt.PyJWTError, KeyError) as exc:
            raise UnauthorizedError(invalid_message) from exc

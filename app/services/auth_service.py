from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException, status

from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.repositories.user_repository import UserRepository
from app.schemas.auth_schemas import LoginSchema, RegisterSchema, TokenResponse


class AuthService:
    def __init__(
        self,
        user_repository: UserRepository,
        refresh_token_repository: RefreshTokenRepository,
    ):
        self.user_repository = user_repository
        self.refresh_token_repository = refresh_token_repository

    async def _issue_tokens(self, user: User) -> TokenResponse:
        access_token = create_access_token(user.id)
        refresh_token, jti, expires_at = create_refresh_token(user.id)
        await self.refresh_token_repository.create(
            RefreshToken(user_id=user.id, jti=jti, expires_at=expires_at)
        )
        return TokenResponse(access_token=access_token, refresh_token=refresh_token)

    async def register(self, data: RegisterSchema) -> tuple[User, TokenResponse]:
        if await self.user_repository.get_by_email(data.email):
            raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered")
        if await self.user_repository.get_by_username(data.username):
            raise HTTPException(status.HTTP_409_CONFLICT, "Username already taken")

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
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid credentials")

        tokens = await self._issue_tokens(user)
        return user, tokens

    async def refresh(self, refresh_token: str) -> TokenResponse:
        try:
            payload = decode_token(refresh_token)
            jti = payload["jti"]
        except Exception as exc:
            raise HTTPException(
                status.HTTP_401_UNAUTHORIZED, "Invalid refresh token"
            ) from exc

        stored = await self.refresh_token_repository.get_by_jti(jti)
        if not stored or stored.revoked_at is not None:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Refresh token revoked")
        if stored.expires_at <= datetime.now(UTC):
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Refresh token expired")

        user = await self.user_repository.get_by_id(stored.user_id)
        if not user:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User not found")

        await self.refresh_token_repository.revoke(jti)
        return await self._issue_tokens(user)

    async def logout(self, refresh_token: str) -> None:
        try:
            payload = decode_token(refresh_token)
            jti = payload["jti"]
        except Exception as exc:
            raise HTTPException(
                status.HTTP_401_UNAUTHORIZED, "Invalid refresh token"
            ) from exc
        await self.refresh_token_repository.revoke(jti)

    async def get_current_user(self, access_token: str) -> User:
        try:
            payload = decode_token(access_token)
            user_id = UUID(payload["sub"])
        except Exception as exc:
            raise HTTPException(
                status.HTTP_401_UNAUTHORIZED, "Invalid access token"
            ) from exc

        user = await self.user_repository.get_by_id(user_id)
        if not user or not user.is_active:
            raise HTTPException(
                status.HTTP_401_UNAUTHORIZED, "User not found or inactive"
            )
        return user

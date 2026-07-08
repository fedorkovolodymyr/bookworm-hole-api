from datetime import UTC, datetime, timedelta
from uuid import UUID

import jwt

from app.core.errors import (
    ConflictError,
    ErrorMessages,
    NotFoundError,
    UnauthorizedError,
)
from app.core.security import create_password_reset_token, decode_token
from app.models.password_reset_token import PasswordResetToken
from app.models.user import User
from app.repositories.collection_repository import CollectionRepository
from app.repositories.password_reset_token_repository import (
    PasswordResetTokenRepository,
)
from app.repositories.user_repository import UserRepository
from app.schemas.collection_schemas import CollectionResponse
from app.schemas.common_schemas import Page
from app.schemas.user_schemas import (
    AdminUserResponse,
    ChangePasswordSchema,
    PasswordResetTokenResponse,
    PublicUserProfileResponse,
    UpdateUserSchema,
)
from app.services.security import hash_password, verify_password

DELETION_GRACE_PERIOD_DAYS = 30


class UserService:
    def __init__(
        self,
        user_repository: UserRepository,
        collection_repository: CollectionRepository,
        password_reset_token_repository: PasswordResetTokenRepository | None = None,
    ):
        self.user_repository = user_repository
        self.collection_repository = collection_repository
        self.password_reset_token_repository = password_reset_token_repository

    async def update_profile(self, user_id: UUID, data: UpdateUserSchema) -> User:
        user = await self.user_repository.update(user_id, data)
        if not user:
            raise NotFoundError(ErrorMessages.USER_NOT_FOUND)
        return user

    async def change_password(self, user_id: UUID, data: ChangePasswordSchema) -> None:
        user = await self.user_repository.get_by_id(user_id)
        if not user:
            raise NotFoundError(ErrorMessages.USER_NOT_FOUND)
        if not user.password_hash or not verify_password(
            data.current_password, user.password_hash
        ):
            raise UnauthorizedError(ErrorMessages.INVALID_CURRENT_PASSWORD)
        await self.user_repository.update_password(
            user_id, hash_password(data.new_password)
        )

    async def deactivate(self, user_id: UUID) -> User:
        user = await self.user_repository.deactivate(user_id)
        if not user:
            raise NotFoundError(ErrorMessages.USER_NOT_FOUND)
        return user

    async def schedule_deletion(self, user_id: UUID) -> User:
        scheduled_at = datetime.now(UTC) + timedelta(days=DELETION_GRACE_PERIOD_DAYS)
        user = await self.user_repository.schedule_deletion(user_id, scheduled_at)
        if not user:
            raise NotFoundError(ErrorMessages.USER_NOT_FOUND)
        return user

    async def cancel_deletion(self, user_id: UUID) -> User:
        user = await self.user_repository.get_by_id(user_id)
        if not user:
            raise NotFoundError(ErrorMessages.USER_NOT_FOUND)
        if user.deletion_scheduled_at is None:
            raise ConflictError(ErrorMessages.DELETION_NOT_SCHEDULED)
        if user.deletion_scheduled_at <= datetime.now(UTC):
            raise ConflictError(ErrorMessages.DELETION_GRACE_PERIOD_EXPIRED)
        cancelled = await self.user_repository.cancel_deletion(user_id)
        if not cancelled:
            raise NotFoundError(ErrorMessages.USER_NOT_FOUND)
        return cancelled

    async def get_public_profile(
        self, username: str, skip: int = 0, limit: int = 10
    ) -> PublicUserProfileResponse:
        user = await self.user_repository.get_by_username(username)
        if not user:
            raise NotFoundError(ErrorMessages.USER_NOT_FOUND)
        collections, total = await self.collection_repository.get_public_for_user(
            user.id, skip, limit
        )
        return PublicUserProfileResponse(
            username=user.username,
            display_name=user.display_name,
            bio=user.bio,
            avatar_url=user.avatar_url,
            collections=Page(
                items=[
                    CollectionResponse.model_validate(collection)
                    for collection in collections
                ],
                total=total,
                limit=limit,
                offset=skip,
            ),
        )

    async def list_users(
        self,
        skip: int = 0,
        limit: int = 10,
        email: str | None = None,
        username: str | None = None,
        is_active: bool | None = None,
        is_admin: bool | None = None,
    ) -> Page[AdminUserResponse]:
        users, total = await self.user_repository.get_all(
            skip=skip,
            limit=limit,
            email=email,
            username=username,
            is_active=is_active,
            is_admin=is_admin,
        )
        return Page(
            items=[AdminUserResponse.model_validate(user) for user in users],
            total=total,
            limit=limit,
            offset=skip,
        )

    async def activate_user(self, user_id: UUID) -> User:
        user = await self.user_repository.activate(user_id)
        if not user:
            raise NotFoundError(ErrorMessages.USER_NOT_FOUND)
        return user

    async def promote_user(self, user_id: UUID) -> User:
        user = await self.user_repository.promote(user_id)
        if not user:
            raise NotFoundError(ErrorMessages.USER_NOT_FOUND)
        return user

    async def demote_user(self, user_id: UUID) -> User:
        user = await self.user_repository.demote(user_id)
        if not user:
            raise NotFoundError(ErrorMessages.USER_NOT_FOUND)
        return user

    async def issue_password_reset(self, user_id: UUID) -> PasswordResetTokenResponse:
        user = await self.user_repository.get_by_id(user_id)
        if not user:
            raise NotFoundError(ErrorMessages.USER_NOT_FOUND)

        if not self.password_reset_token_repository:
            raise ValueError("Password reset token repository not initialized")

        token_str, jti, expires_at = create_password_reset_token(user_id)
        reset_token = PasswordResetToken(
            user_id=user_id, jti=jti, expires_at=expires_at
        )
        await self.password_reset_token_repository.create(reset_token)

        return PasswordResetTokenResponse(reset_token=token_str)

    async def reset_password_with_token(
        self, reset_token: str, new_password: str
    ) -> User:
        if not self.password_reset_token_repository:
            raise ValueError("Password reset token repository not initialized")

        try:
            payload = decode_token(reset_token)
        except jwt.PyJWTError as err:
            raise NotFoundError(ErrorMessages.PASSWORD_RESET_TOKEN_INVALID) from err

        jti = payload.get("jti")
        user_id_str = payload.get("sub")

        if not jti or not user_id_str:
            raise NotFoundError(ErrorMessages.PASSWORD_RESET_TOKEN_INVALID)

        token_record = await self.password_reset_token_repository.get_by_jti(jti)
        if not token_record:
            raise NotFoundError(ErrorMessages.PASSWORD_RESET_TOKEN_INVALID)

        if token_record.used_at:
            raise UnauthorizedError(ErrorMessages.PASSWORD_RESET_TOKEN_USED)

        if datetime.now(UTC) > token_record.expires_at:
            raise UnauthorizedError(ErrorMessages.PASSWORD_RESET_TOKEN_EXPIRED)

        user_id = UUID(user_id_str)
        user = await self.user_repository.get_by_id(user_id)
        if not user:
            raise NotFoundError(ErrorMessages.USER_NOT_FOUND)

        await self.user_repository.update_password(user_id, hash_password(new_password))
        await self.password_reset_token_repository.mark_used(jti)

        user = await self.user_repository.get_by_id(user_id)
        if not user:
            raise NotFoundError(ErrorMessages.USER_NOT_FOUND)
        return user

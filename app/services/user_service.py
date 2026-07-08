from datetime import UTC, datetime, timedelta
from uuid import UUID

from app.core.errors import (
    ConflictError,
    ErrorMessages,
    NotFoundError,
    UnauthorizedError,
)
from app.models.user import User
from app.repositories.collection_repository import CollectionRepository
from app.repositories.user_repository import UserRepository
from app.schemas.collection_schemas import CollectionResponse
from app.schemas.common_schemas import Page
from app.schemas.user_schemas import (
    ChangePasswordSchema,
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
    ):
        self.user_repository = user_repository
        self.collection_repository = collection_repository

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

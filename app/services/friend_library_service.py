from uuid import UUID

from app.core.errors import ErrorMessages, NotFoundError, UnauthorizedError
from app.models.friendship import FriendshipStatus
from app.repositories.book_status_repository import BookStatusRepository
from app.repositories.collection_repository import CollectionRepository
from app.repositories.friendship_repository import FriendshipRepository
from app.repositories.user_repository import UserRepository
from app.schemas.book_status_schemas import BookStatusResponse
from app.schemas.collection_schemas import CollectionResponse
from app.schemas.common_schemas import Page


class FriendLibraryService:
    def __init__(
        self,
        friendship_repo: FriendshipRepository,
        user_repo: UserRepository,
        book_status_repo: BookStatusRepository,
        collection_repo: CollectionRepository,
    ) -> None:
        self.friendship_repo = friendship_repo
        self.user_repo = user_repo
        self.book_status_repo = book_status_repo
        self.collection_repo = collection_repo

    async def _verify_visible_friend(self, viewer_id: UUID, target_id: UUID) -> None:
        friendship = await self.friendship_repo.get_between(viewer_id, target_id)
        if not friendship or friendship.status != FriendshipStatus.accepted:
            raise NotFoundError(ErrorMessages.FRIENDSHIP_NOT_FOUND)

        target = await self.user_repo.get_by_id(target_id)
        if not target:
            raise NotFoundError(ErrorMessages.USER_NOT_FOUND)
        if not target.friends_can_see_library:
            raise UnauthorizedError(ErrorMessages.USER_BLOCKED)

    async def get_library(
        self, viewer_id: UUID, target_id: UUID, skip: int = 0, limit: int = 10
    ) -> Page[BookStatusResponse]:
        await self._verify_visible_friend(viewer_id, target_id)
        statuses, total = await self.book_status_repo.get_library_for_user(
            target_id, skip, limit
        )
        return Page(
            items=[BookStatusResponse.model_validate(s) for s in statuses],
            total=total,
            limit=limit,
            offset=skip,
        )

    async def get_collections(
        self, viewer_id: UUID, target_id: UUID, skip: int = 0, limit: int = 10
    ) -> Page[CollectionResponse]:
        await self._verify_visible_friend(viewer_id, target_id)
        collections, total = await self.collection_repo.get_public_for_user(
            target_id, skip, limit
        )
        return Page(
            items=[CollectionResponse.model_validate(c) for c in collections],
            total=total,
            limit=limit,
            offset=skip,
        )

import asyncio

from app.models.user import User
from app.repositories.book_status_repository import BookStatusRepository
from app.repositories.collection_repository import CollectionRepository
from app.repositories.friendship_repository import FriendshipRepository
from app.repositories.reading_session_repository import ReadingSessionRepository
from app.repositories.review_repository import ReviewRepository
from app.schemas.export_schemas import (
    AccountExportResponse,
    ExportBookStatusResponse,
    ExportCollectionResponse,
    ExportFriendResponse,
    ExportReadingSessionResponse,
    ExportReviewResponse,
    ExportUserResponse,
)


class UserExportService:
    def __init__(
        self,
        user: User,
        collection_repository: CollectionRepository,
        book_status_repository: BookStatusRepository,
        review_repository: ReviewRepository,
        reading_session_repository: ReadingSessionRepository,
        friendship_repository: FriendshipRepository,
    ):
        self.user = user
        self.collection_repository = collection_repository
        self.book_status_repository = book_status_repository
        self.review_repository = review_repository
        self.reading_session_repository = reading_session_repository
        self.friendship_repository = friendship_repository

    async def export_account(self) -> AccountExportResponse:
        user_id = self.user.id

        (
            collections_tuple,
            book_statuses,
            reviews,
            sessions,
            friends_pairs,
        ) = await asyncio.gather(
            self.collection_repository.get_all_for_user(user_id, skip=0, limit=10000),
            self.book_status_repository.get_all_for_user(user_id),
            self.review_repository.get_all_for_user(user_id),
            self.reading_session_repository.get_all_for_user(user_id),
            self.friendship_repository.list_friends(user_id),
        )
        collections = collections_tuple[0]

        return AccountExportResponse(
            export_version=1,
            user=ExportUserResponse.model_validate(self.user),
            collections=[
                ExportCollectionResponse.model_validate(c) for c in collections
            ],
            statuses=[
                ExportBookStatusResponse.model_validate(s) for s in book_statuses
            ],
            reviews=[ExportReviewResponse.model_validate(r) for r in reviews],
            reading_sessions=[
                ExportReadingSessionResponse.model_validate(s) for s in sessions
            ],
            friends=[
                ExportFriendResponse(
                    user_id=friend.id,
                    username=friend.username,
                    display_name=friend.display_name,
                    avatar_url=friend.avatar_url,
                    since=friendship.responded_at or friendship.created_at,
                )
                for friendship, friend in friends_pairs
            ],
        )

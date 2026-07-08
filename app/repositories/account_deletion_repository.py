from uuid import UUID

from sqlalchemy import delete, or_, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col

from app.models.book_status import BookStatus
from app.models.collection import Collection
from app.models.contribution import Contribution
from app.models.friendship import Friendship
from app.models.reading_session import ReadingSession
from app.models.review import Review
from app.models.user import User


class AccountDeletionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def purge_user_data(self, user_id: UUID) -> None:
        """Anonymize/detach then hard-delete everything a purged user owns.

        Runs before `delete_user` so no FK still points at the user row.
        """
        await self.session.execute(
            update(Review).where(col(Review.user_id) == user_id).values(user_id=None)
        )
        await self.session.execute(
            update(BookStatus)
            .where(col(BookStatus.lent_to_user_id) == user_id)
            .values(lent_to_user_id=None)
        )
        await self.session.execute(
            update(Contribution)
            .where(col(Contribution.reviewer_id) == user_id)
            .values(reviewer_id=None)
        )
        await self.session.execute(
            delete(ReadingSession).where(col(ReadingSession.user_id) == user_id)
        )
        await self.session.execute(
            delete(BookStatus).where(col(BookStatus.user_id) == user_id)
        )
        await self.session.execute(
            delete(Collection).where(col(Collection.user_id) == user_id)
        )
        await self.session.execute(
            delete(Friendship).where(
                or_(
                    col(Friendship.requester_id) == user_id,
                    col(Friendship.addressee_id) == user_id,
                )
            )
        )
        await self.session.execute(
            delete(Contribution).where(col(Contribution.user_id) == user_id)
        )
        await self.session.commit()

    async def delete_user(self, user_id: UUID) -> None:
        user = await self.session.get(User, user_id)
        if not user:
            return
        await self.session.delete(user)
        await self.session.commit()

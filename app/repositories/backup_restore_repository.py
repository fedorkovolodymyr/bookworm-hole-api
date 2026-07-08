from datetime import datetime
from uuid import UUID

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col, select

from app.models.book_status import BookStatus, BookStatusKind
from app.models.collection import Collection
from app.models.reading_session import ReadingSession
from app.models.review import Review


class BackupRestoreRepository:
    """DB access for restoring an account export.

    Natural-key lookups support idempotent merge (create-if-missing). The
    purge + add methods don't commit — `BackupRestoreService` commits once
    after both the wipe and the fresh writes for replace mode, so a failure
    partway through rolls back the whole thing instead of leaving the
    account half-wiped.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def find_book_status(
        self,
        user_id: UUID,
        book_id: UUID | None,
        release_id: UUID | None,
        status: BookStatusKind,
    ) -> BookStatus | None:
        query = select(BookStatus).where(
            col(BookStatus.user_id) == user_id,
            col(BookStatus.book_id) == book_id,
            col(BookStatus.release_id) == release_id,
            col(BookStatus.status) == status,
        )
        result = await self.session.execute(query)
        return result.scalars().first()

    async def find_collection(self, user_id: UUID, name: str) -> Collection | None:
        query = select(Collection).where(
            col(Collection.user_id) == user_id, col(Collection.name) == name
        )
        result = await self.session.execute(query)
        return result.scalars().first()

    async def find_reading_session(
        self, user_id: UUID, release_id: UUID, started_at: datetime
    ) -> ReadingSession | None:
        query = select(ReadingSession).where(
            col(ReadingSession.user_id) == user_id,
            col(ReadingSession.release_id) == release_id,
            col(ReadingSession.started_at) == started_at,
        )
        result = await self.session.execute(query)
        return result.scalars().first()

    def add(self, entity: BookStatus | Collection | Review | ReadingSession) -> None:
        self.session.add(entity)

    async def purge_owned_data(self, user_id: UUID) -> None:
        """Hard-deletes the user's collections/statuses/reviews/reading
        sessions ahead of a replace-mode restore. Scoped to only what an
        account export covers — unlike account deletion, this leaves the
        User row, friendships, and contributions untouched."""
        await self.session.execute(
            delete(Collection).where(col(Collection.user_id) == user_id)
        )
        await self.session.execute(
            delete(BookStatus).where(col(BookStatus.user_id) == user_id)
        )
        await self.session.execute(delete(Review).where(col(Review.user_id) == user_id))
        await self.session.execute(
            delete(ReadingSession).where(col(ReadingSession.user_id) == user_id)
        )

    async def commit(self) -> None:
        await self.session.commit()

    async def rollback(self) -> None:
        await self.session.rollback()

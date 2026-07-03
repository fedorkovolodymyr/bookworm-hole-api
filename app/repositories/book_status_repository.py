from typing import Sequence
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col, select

from app.models.book_status import BookStatus, BookStatusKind
from app.schemas.book_status_schemas import UpdateBookStatusSchema


class BookStatusRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, book_status: BookStatus) -> BookStatus:
        self.session.add(book_status)
        await self.session.commit()
        await self.session.refresh(book_status)
        return book_status

    async def get_by_id(self, book_status_id: UUID) -> BookStatus | None:
        return await self.session.get(BookStatus, book_status_id)

    async def get_all_for_user(
        self, user_id: UUID, status: BookStatusKind | None = None
    ) -> Sequence[BookStatus]:
        query = select(BookStatus).where(col(BookStatus.user_id) == user_id)
        if status:
            query = query.where(col(BookStatus.status) == status)
        result = await self.session.execute(query)
        return result.scalars().all()

    async def update(
        self, book_status_id: UUID, data: UpdateBookStatusSchema
    ) -> BookStatus | None:
        book_status = await self.session.get(BookStatus, book_status_id)
        if not book_status:
            return None
        book_status.sqlmodel_update(data.model_dump(exclude_unset=True))
        self.session.add(book_status)
        await self.session.commit()
        await self.session.refresh(book_status)
        return book_status

    async def save(self, book_status: BookStatus) -> BookStatus:
        self.session.add(book_status)
        await self.session.commit()
        await self.session.refresh(book_status)
        return book_status

    async def delete(self, book_status_id: UUID) -> bool:
        book_status = await self.session.get(BookStatus, book_status_id)
        if not book_status:
            return False
        await self.session.delete(book_status)
        await self.session.commit()
        return True

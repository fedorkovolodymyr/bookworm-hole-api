from collections.abc import Sequence
from typing import Literal
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased
from sqlmodel import col, select

from app.models.book_status import BookStatus, BookStatusKind
from app.models.catalog import Book, Release
from app.schemas.book_status_schemas import UpdateBookStatusSchema

BookStatusSort = Literal["acquired_at", "title"]


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

    async def get_page_for_user(
        self,
        user_id: UUID,
        status: BookStatusKind,
        sort: BookStatusSort,
        skip: int = 0,
        limit: int = 10,
    ) -> tuple[Sequence[BookStatus], int]:
        filters = (
            col(BookStatus.user_id) == user_id,
            col(BookStatus.status) == status,
        )
        count_query = select(func.count()).select_from(
            select(BookStatus.id).where(*filters).subquery()
        )
        total = (await self.session.execute(count_query)).scalar_one()

        release_book = aliased(Book)
        query = (
            select(BookStatus)
            .outerjoin(Book, col(BookStatus.book_id) == Book.id)
            .outerjoin(Release, col(BookStatus.release_id) == Release.id)
            .outerjoin(release_book, col(Release.book_id) == release_book.id)
            .where(*filters)
        )
        if sort == "title":
            title = func.coalesce(release_book.title, Book.title)
            query = query.order_by(title.asc())
        else:
            query = query.order_by(col(BookStatus.acquired_at).desc())

        result = await self.session.execute(query.offset(skip).limit(limit))
        return result.scalars().all(), total

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

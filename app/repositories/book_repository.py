from typing import Sequence
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlmodel import col, select

from app.models.catalog import ISBN, Book, Release


class BookRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, book: Book) -> Book:
        self.session.add(book)
        await self.session.commit()
        await self.session.refresh(book)
        return book

    async def get_by_id(self, book_id: UUID) -> Book | None:
        return await self.session.get(Book, book_id)

    async def get_by_isbn(self, code_normalized: str) -> Book | None:
        result = await self.session.execute(
            select(Book)
            .join(Release, col(Release.book_id) == col(Book.id))
            .join(ISBN, col(ISBN.release_id) == col(Release.id))
            .where(col(ISBN.code_normalized) == code_normalized)
            .options(selectinload(Book.releases).selectinload(Release.isbns))  # pyright: ignore[reportArgumentType]
        )
        return result.scalars().first()

    async def get_all(self, skip: int = 0, limit: int = 10) -> Sequence[Book]:
        result = await self.session.execute(select(Book).offset(skip).limit(limit))
        return result.scalars().all()

    async def update(self, book_id: UUID, data: dict) -> Book | None:  # type: ignore[type-arg]
        book = await self.session.get(Book, book_id)
        if not book:
            return None
        for key, value in data.items():
            setattr(book, key, value)
        self.session.add(book)
        await self.session.commit()
        await self.session.refresh(book)
        return book

    async def delete(self, book_id: UUID) -> bool:
        book = await self.session.get(Book, book_id)
        if not book:
            return False
        await self.session.delete(book)
        await self.session.commit()
        return True

from typing import Sequence
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlmodel import col, select

from app.models.catalog import ISBN, Book, BookContributor, Contributor, Release
from app.schemas.book_schemas import UpdateBookSchema


class BookRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, book: Book) -> Book:
        self.session.add(book)
        await self.session.commit()
        await self.session.refresh(book)
        return book

    async def get_by_id(self, book_id: UUID) -> Book | None:
        result = await self.session.execute(
            select(Book)
            .where(col(Book.id) == book_id)
            .options(selectinload(Book.releases).selectinload(Release.isbns))  # pyright: ignore[reportArgumentType]
        )
        return result.scalars().first()

    async def get_by_isbn(self, code_normalized: str) -> Book | None:
        result = await self.session.execute(
            select(Book)
            .join(Release, col(Release.book_id) == col(Book.id))
            .join(ISBN, col(ISBN.release_id) == col(Release.id))
            .where(col(ISBN.code_normalized) == code_normalized)
            .options(selectinload(Book.releases).selectinload(Release.isbns))  # pyright: ignore[reportArgumentType]
        )
        return result.scalars().first()

    async def get_all(
        self,
        skip: int = 0,
        limit: int = 10,
        title: str | None = None,
        author: str | None = None,
        language: str | None = None,
    ) -> tuple[Sequence[Book], int]:
        filters = []
        if title:
            filters.append(col(Book.title).ilike(f"%{title}%"))
        if language:
            filters.append(col(Release.language) == language)

        base = select(Book)
        count_query = select(func.count(func.distinct(Book.id)))
        if language:
            base = base.join(Release, col(Release.book_id) == col(Book.id))
            count_query = count_query.join(
                Release, col(Release.book_id) == col(Book.id)
            )
        if author:
            base = base.join(
                BookContributor, col(BookContributor.book_id) == col(Book.id)
            ).join(
                Contributor,
                col(Contributor.id) == col(BookContributor.contributor_id),
            )
            count_query = count_query.join(
                BookContributor, col(BookContributor.book_id) == col(Book.id)
            ).join(
                Contributor,
                col(Contributor.id) == col(BookContributor.contributor_id),
            )
            filters.append(col(Contributor.full_name).ilike(f"%{author}%"))

        for condition in filters:
            base = base.where(condition)
            count_query = count_query.where(condition)

        total = (await self.session.execute(count_query)).scalar_one()
        result = await self.session.execute(base.distinct().offset(skip).limit(limit))
        return result.scalars().all(), total

    async def update(self, book_id: UUID, data: UpdateBookSchema) -> Book | None:
        book = await self.session.get(Book, book_id)
        if not book:
            return None
        book.sqlmodel_update(data.model_dump(exclude_unset=True))
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

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import ColumnElement, delete, func, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col, select

from app.models.book_status import BookStatus
from app.models.catalog import ISBN, Book, BookContributor, Contributor, Release
from app.models.collection import CollectionItem
from app.models.review import Review
from app.repositories.loading import eager, eager_nested
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
            .options(
                eager_nested(Book.releases, Release.isbns),
                eager(Book.contributors),
            )
            .execution_options(populate_existing=True)
        )
        return result.scalars().first()

    async def get_by_isbn(self, code_normalized: str) -> Book | None:
        result = await self.session.execute(
            select(Book)
            .join(Release, col(Release.book_id) == col(Book.id))
            .join(ISBN, col(ISBN.release_id) == col(Release.id))
            .where(col(ISBN.code_normalized) == code_normalized)
            .options(eager_nested(Book.releases, Release.isbns))
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
        filters: list[ColumnElement[bool]] = []
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

    async def merge(self, source_id: UUID, target_id: UUID) -> Book | None:
        """Reassign everything pointing at ``source_id`` to ``target_id``, then
        delete the source book. Runs as a single transaction: if any step fails,
        the caller's session rollback (see ``get_session``) undoes all of it.
        """
        source = await self.session.get(Book, source_id)
        target = await self.session.get(Book, target_id)
        if source is None or target is None:
            return None

        await self.session.execute(
            update(Release)
            .where(col(Release.book_id) == source_id)
            .values(book_id=target_id)
        )

        # Reviews are unique per (user, book); drop the source-side row where the
        # user already reviewed the target book directly to avoid a conflict.
        await self.session.execute(
            delete(Review).where(
                col(Review.book_id) == source_id,
                col(Review.user_id).in_(
                    select(Review.user_id).where(col(Review.book_id) == target_id)
                ),
            )
        )
        await self.session.execute(
            update(Review)
            .where(col(Review.book_id) == source_id)
            .values(book_id=target_id)
        )

        await self.session.execute(
            update(BookStatus)
            .where(col(BookStatus.book_id) == source_id)
            .values(book_id=target_id)
        )
        await self.session.execute(
            update(CollectionItem)
            .where(col(CollectionItem.book_id) == source_id)
            .values(book_id=target_id)
        )

        await self.session.delete(source)
        await self.session.commit()
        return await self.get_by_id(target_id)

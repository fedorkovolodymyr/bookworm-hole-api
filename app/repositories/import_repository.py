from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlmodel import col, select

from app.models.catalog import (
    ISBN,
    Book,
    BookContributor,
    ContributorRole,
    ISBNKind,
    Release,
    ReleaseContributor,
    ReleaseFormat,
)


class ImportRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def find_book_by_title_and_contributors(
        self, title: str, contributor_ids: list[UUID]
    ) -> Book | None:
        if not contributor_ids:
            return None
        target = set(contributor_ids)
        result = await self.session.execute(
            select(Book)
            .where(col(Book.title) == title)
            .options(
                selectinload(Book.contributors),  # pyright: ignore[reportArgumentType]
                selectinload(Book.releases).selectinload(Release.isbns),  # pyright: ignore[reportArgumentType]
            )
        )
        for book in result.scalars().all():
            if {contributor.id for contributor in book.contributors} == target:
                return book
        return None

    async def add_book(
        self,
        *,
        title: str,
        description: str,
        first_publication_year: int | None,
    ) -> Book:
        book = Book(
            title=title,
            description=description,
            first_publication_year=first_publication_year,
        )
        self.session.add(book)
        await self.session.flush()
        return book

    async def add_release(
        self,
        *,
        book_id: UUID,
        format: ReleaseFormat,
        publisher: str,
        published_year: int | None,
        language: str,
    ) -> Release:
        release = Release(
            book_id=book_id,
            format=format,
            publisher=publisher,
            published_year=published_year,
            language=language,
        )
        self.session.add(release)
        await self.session.flush()
        return release

    async def add_isbn(
        self,
        *,
        release_id: UUID,
        code_normalized: str,
        code_original: str,
        kind: ISBNKind,
    ) -> ISBN:
        isbn = ISBN(
            release_id=release_id,
            code_normalized=code_normalized,
            code_original=code_original,
            kind=kind,
            created_at=datetime.now(UTC),
        )
        self.session.add(isbn)
        await self.session.flush()
        return isbn

    async def link_book_contributor(
        self, book_id: UUID, contributor_id: UUID, role: ContributorRole
    ) -> None:
        result = await self.session.execute(
            select(BookContributor)
            .where(col(BookContributor.book_id) == book_id)
            .where(col(BookContributor.contributor_id) == contributor_id)
        )
        if result.scalars().first():
            return
        self.session.add(
            BookContributor(book_id=book_id, contributor_id=contributor_id, role=role)
        )
        await self.session.flush()

    async def link_release_contributor(
        self, release_id: UUID, contributor_id: UUID, role: ContributorRole
    ) -> None:
        result = await self.session.execute(
            select(ReleaseContributor)
            .where(col(ReleaseContributor.release_id) == release_id)
            .where(col(ReleaseContributor.contributor_id) == contributor_id)
        )
        if result.scalars().first():
            return
        self.session.add(
            ReleaseContributor(
                release_id=release_id, contributor_id=contributor_id, role=role
            )
        )
        await self.session.flush()

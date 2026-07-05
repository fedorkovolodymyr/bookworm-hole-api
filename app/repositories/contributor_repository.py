import re
from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import ColumnElement, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col, select

from app.models.catalog import (
    Book,
    BookContributor,
    Contributor,
    ContributorRole,
    Release,
    ReleaseContributor,
)
from app.schemas.contributor_schemas import UpdateContributorSchema

_SLUG_INVALID_CHARS = re.compile(r"[^a-z0-9]+")


def slugify(value: str) -> str:
    slug = _SLUG_INVALID_CHARS.sub("-", value.lower()).strip("-")
    return slug or "contributor"


class ContributorRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_name(self, full_name: str, sort_name: str) -> Contributor | None:
        result = await self.session.execute(
            select(Contributor)
            .where(col(Contributor.full_name) == full_name)
            .where(col(Contributor.sort_name) == sort_name)
        )
        return result.scalars().first()

    async def get_by_id(self, contributor_id: UUID) -> Contributor | None:
        return await self.session.get(Contributor, contributor_id)

    async def get_all(
        self,
        skip: int = 0,
        limit: int = 10,
        name: str | None = None,
        role: ContributorRole | None = None,
    ) -> tuple[Sequence[Contributor], int]:
        filters: list[ColumnElement[bool]] = []
        if name:
            filters.append(
                or_(
                    col(Contributor.full_name).ilike(f"%{name}%"),
                    col(Contributor.sort_name).ilike(f"%{name}%"),
                )
            )
        if role:
            filters.append(
                col(Contributor.id).in_(
                    select(BookContributor.contributor_id)
                    .where(col(BookContributor.role) == role)
                    .union(
                        select(ReleaseContributor.contributor_id).where(
                            col(ReleaseContributor.role) == role
                        )
                    )
                )
            )

        base = select(Contributor)
        count_query = select(func.count(func.distinct(Contributor.id)))
        for condition in filters:
            base = base.where(condition)
            count_query = count_query.where(condition)

        total = (await self.session.execute(count_query)).scalar_one()
        result = await self.session.execute(
            base.order_by(col(Contributor.sort_name)).offset(skip).limit(limit)
        )
        return result.scalars().all(), total

    async def get_books_by_role(
        self, contributor_id: UUID
    ) -> Sequence[tuple[Book, ContributorRole]]:
        result = await self.session.execute(
            select(Book, BookContributor.role)
            .join(BookContributor, col(BookContributor.book_id) == col(Book.id))
            .where(col(BookContributor.contributor_id) == contributor_id)
        )
        return [(book, role) for book, role in result.all()]

    async def get_releases_by_role(
        self, contributor_id: UUID
    ) -> Sequence[tuple[Release, ContributorRole]]:
        result = await self.session.execute(
            select(Release, ReleaseContributor.role)
            .join(
                ReleaseContributor,
                col(ReleaseContributor.release_id) == col(Release.id),
            )
            .where(col(ReleaseContributor.contributor_id) == contributor_id)
        )
        return [(release, role) for release, role in result.all()]

    async def get_books(
        self, contributor_id: UUID, skip: int = 0, limit: int = 10
    ) -> tuple[Sequence[Book], int]:
        base = (
            select(Book)
            .join(BookContributor, col(BookContributor.book_id) == col(Book.id))
            .where(col(BookContributor.contributor_id) == contributor_id)
        )
        count_query = (
            select(func.count(func.distinct(Book.id)))
            .join(BookContributor, col(BookContributor.book_id) == col(Book.id))
            .where(col(BookContributor.contributor_id) == contributor_id)
        )
        total = (await self.session.execute(count_query)).scalar_one()
        result = await self.session.execute(
            base.distinct().order_by(col(Book.title)).offset(skip).limit(limit)
        )
        return result.scalars().all(), total

    async def add(
        self,
        full_name: str,
        sort_name: str,
        birth_year: int | None = None,
        death_year: int | None = None,
        bio: str | None = None,
    ) -> Contributor:
        """Flush-only create; caller owns the transaction commit."""
        slug = await self._unique_slug(slugify(full_name))
        contributor = Contributor(
            full_name=full_name,
            sort_name=sort_name,
            birth_year=birth_year,
            death_year=death_year,
            bio=bio,
            slug=slug,
        )
        self.session.add(contributor)
        await self.session.flush()
        return contributor

    async def create(
        self,
        full_name: str,
        sort_name: str,
        birth_year: int | None = None,
        death_year: int | None = None,
        bio: str | None = None,
    ) -> Contributor:
        contributor = await self.add(full_name, sort_name, birth_year, death_year, bio)
        await self.session.commit()
        await self.session.refresh(contributor)
        return contributor

    async def update(
        self, contributor_id: UUID, data: UpdateContributorSchema
    ) -> Contributor | None:
        contributor = await self.session.get(Contributor, contributor_id)
        if not contributor:
            return None
        contributor.sqlmodel_update(data.model_dump(exclude_unset=True))
        self.session.add(contributor)
        await self.session.commit()
        await self.session.refresh(contributor)
        return contributor

    async def _unique_slug(self, base: str) -> str:
        slug = base
        suffix = 2
        while await self._slug_exists(slug):
            slug = f"{base}-{suffix}"
            suffix += 1
        return slug

    async def _slug_exists(self, slug: str) -> bool:
        result = await self.session.execute(
            select(Contributor.id).where(col(Contributor.slug) == slug)
        )
        return result.scalars().first() is not None

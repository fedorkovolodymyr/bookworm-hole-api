import re

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col, select

from app.models.catalog import Contributor

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

    async def add(self, full_name: str, sort_name: str) -> Contributor:
        """Flush-only create; caller owns the transaction commit."""
        slug = await self._unique_slug(slugify(full_name))
        contributor = Contributor(full_name=full_name, sort_name=sort_name, slug=slug)
        self.session.add(contributor)
        await self.session.flush()
        return contributor

    async def create(self, full_name: str, sort_name: str) -> Contributor:
        contributor = await self.add(full_name, sort_name)
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

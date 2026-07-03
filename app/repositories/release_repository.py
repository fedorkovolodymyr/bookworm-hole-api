from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlmodel import col, select

from app.models.catalog import Release


class ReleaseRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, release: Release) -> Release:
        self.session.add(release)
        await self.session.commit()
        await self.session.refresh(release)
        return release

    async def get_by_id(self, release_id: UUID) -> Release | None:
        result = await self.session.execute(
            select(Release)
            .where(col(Release.id) == release_id)
            .options(selectinload(Release.isbns))  # pyright: ignore[reportArgumentType]
        )
        return result.scalars().first()

    async def update(self, release_id: UUID, data: dict) -> Release | None:  # type: ignore[type-arg]
        release = await self.session.get(Release, release_id)
        if not release:
            return None
        for key, value in data.items():
            setattr(release, key, value)
        self.session.add(release)
        await self.session.commit()
        return await self.get_by_id(release_id)

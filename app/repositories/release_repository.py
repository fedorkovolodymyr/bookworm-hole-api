from collections.abc import Sequence
from datetime import datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col, or_, select

from app.models.catalog import ISBN, Release
from app.repositories.loading import eager
from app.schemas.book_schemas import UpdateReleaseSchema


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
            .options(eager(Release.isbns))
        )
        return result.scalars().first()

    async def update(
        self, release_id: UUID, data: UpdateReleaseSchema
    ) -> Release | None:
        release = await self.session.get(Release, release_id)
        if not release:
            return None
        release.sqlmodel_update(data.model_dump(exclude_unset=True))
        self.session.add(release)
        await self.session.commit()
        return await self.get_by_id(release_id)

    async def get_stale(self, older_than: datetime) -> Sequence[Release]:
        """Releases with at least one ISBN whose external metadata was never
        synced, or was last synced before `older_than`."""
        result = await self.session.execute(
            select(Release)
            .join(ISBN, col(ISBN.release_id) == col(Release.id))
            .where(
                or_(
                    col(Release.last_external_sync_at).is_(None),
                    col(Release.last_external_sync_at) < older_than,
                )
            )
            .options(eager(Release.isbns))
            .distinct()
        )
        return result.scalars().all()

    async def mark_synced(self, release_id: UUID, synced_at: datetime) -> None:
        release = await self.session.get(Release, release_id)
        if release is None:
            return
        release.last_external_sync_at = synced_at
        self.session.add(release)
        await self.session.commit()

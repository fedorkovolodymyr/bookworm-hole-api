from collections.abc import Sequence
from datetime import datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col, or_, select

from app.models.catalog import ISBN, ContributorRole, Release, ReleaseContributor
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

    async def add_contributor(
        self, release_id: UUID, contributor_id: UUID, role: ContributorRole
    ) -> bool:
        """Add a contributor to a release with a specific role. Returns True if newly
        created, False if the link already existed.
        """
        existing = await self.session.get(
            ReleaseContributor,
            (release_id, contributor_id, role),
        )
        if existing is not None:
            return False

        link = ReleaseContributor(
            release_id=release_id, contributor_id=contributor_id, role=role
        )
        self.session.add(link)
        await self.session.commit()
        return True

    async def remove_contributor(
        self, release_id: UUID, contributor_id: UUID, role: ContributorRole
    ) -> bool:
        """Remove a contributor from a release. Returns True if deleted, False if
        not found."""
        existing = await self.session.get(
            ReleaseContributor,
            (release_id, contributor_id, role),
        )
        if existing is None:
            return False

        await self.session.delete(existing)
        await self.session.commit()
        return True

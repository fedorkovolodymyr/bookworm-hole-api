from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.catalog import Release
from app.repositories.release_repository import ReleaseRepository
from app.services.external.base import BookSourceAdapter, ExternalBookDetail
from app.services.external.registry import get_adapter

_DEFAULT_SOURCE = "open_library"

# Release fields that may be filled in from external metadata, mapped to the
# corresponding attribute on ExternalBookDetail. Fields are only ever filled
# when currently blank on the Release; a differing existing value is logged
# as a conflict and left untouched (user-edited data is never overwritten).
_SYNCABLE_FIELDS = ("publisher", "published_year", "language", "cover_image_url")


@dataclass
class RefreshSummary:
    refreshed: int = 0
    conflicts: int = 0
    skipped: int = 0
    conflict_details: list[str] = field(default_factory=list[str])


class RefreshMetadataService:
    def __init__(
        self,
        session: AsyncSession,
        release_repository: ReleaseRepository,
        source: str = _DEFAULT_SOURCE,
    ) -> None:
        self.session = session
        self.release_repository = release_repository
        self.source = source

    async def refresh_stale_releases(self, older_than_days: int) -> RefreshSummary:
        cutoff = datetime.now(UTC) - timedelta(days=older_than_days)
        stale_releases = await self.release_repository.get_stale(cutoff)
        adapter = get_adapter(self.source)

        summary = RefreshSummary()
        for release in stale_releases:
            await self._refresh_release(release, adapter, summary)
        return summary

    async def _refresh_release(
        self, release: Release, adapter: BookSourceAdapter, summary: RefreshSummary
    ) -> None:
        isbn = next(iter(release.isbns), None)
        if isbn is None:
            summary.skipped += 1
            return

        detail = await adapter.get_detail(isbn.code_normalized, self.session)
        if detail is None:
            summary.skipped += 1
            return

        self._apply_detail(release, detail, summary)
        await self.release_repository.mark_synced(release.id, datetime.now(UTC))
        summary.refreshed += 1

    def _apply_detail(
        self, release: Release, detail: ExternalBookDetail, summary: RefreshSummary
    ) -> None:
        for field_name in _SYNCABLE_FIELDS:
            external_value = getattr(detail, field_name)
            if not external_value:
                continue

            current_value = getattr(release, field_name)
            if not current_value:
                setattr(release, field_name, external_value)
            elif current_value != external_value:
                summary.conflicts += 1
                conflict = (
                    f"release={release.id} field={field_name} "
                    f"existing={current_value!r} external={external_value!r}"
                )
                summary.conflict_details.append(conflict)
                logger.warning(f"Metadata sync conflict, not overwritten: {conflict}")

        self.session.add(release)

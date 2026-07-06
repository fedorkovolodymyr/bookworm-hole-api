from datetime import UTC, datetime, timedelta
from typing import ClassVar

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.catalog import ISBN, Book, ISBNKind, Release, ReleaseFormat
from app.models.external_source import ExternalSourceRecord
from app.repositories.release_repository import ReleaseRepository
from app.services.external.base import (
    BookSourceAdapter,
    ExternalBookDetail,
)
from app.services.external.registry import _registry, register_adapter
from app.services.refresh_metadata_service import RefreshMetadataService

_FAKE_SOURCE = "fake_refresh_source"


class FakeAdapter(BookSourceAdapter):
    name = _FAKE_SOURCE
    details_by_isbn: ClassVar[dict[str, ExternalBookDetail | None]] = {}

    async def search(
        self, query: str, session: AsyncSession
    ) -> list[ExternalSourceRecord]:
        return []

    async def get_by_isbn(
        self, isbn: str, session: AsyncSession
    ) -> ExternalSourceRecord | None:
        return None

    async def get_detail(
        self, source_id: str, session: AsyncSession
    ) -> ExternalBookDetail | None:
        return self.details_by_isbn.get(source_id)


@pytest.fixture(autouse=True)
def _register_fake_adapter():
    register_adapter(_FAKE_SOURCE)(FakeAdapter)
    yield
    _registry.pop(_FAKE_SOURCE, None)
    FakeAdapter.details_by_isbn = {}


async def _make_release(
    db_session: AsyncSession,
    *,
    isbn_code: str,
    publisher: str = "",
    language: str = "",
    cover_image_url: str | None = None,
    last_external_sync_at: datetime | None = None,
) -> Release:
    book = Book(title="Dune", description="Desert planet epic")
    db_session.add(book)
    await db_session.flush()

    release = Release(
        book_id=book.id,
        format=ReleaseFormat.hardcover,
        publisher=publisher,
        language=language,
        cover_image_url=cover_image_url,
        last_external_sync_at=last_external_sync_at,
    )
    db_session.add(release)
    await db_session.flush()

    db_session.add(
        ISBN(
            release_id=release.id,
            code_normalized=isbn_code,
            code_original=isbn_code,
            kind=ISBNKind.isbn13,
        )
    )
    await db_session.commit()
    return release


def _detail(**overrides: object) -> ExternalBookDetail:
    defaults: dict[str, object] = {
        "title": "Dune",
        "description": "Desert planet epic",
        "contributors": [],
        "isbns": [],
        "format": ReleaseFormat.hardcover,
        "publisher": "Ace Books",
        "published_year": 1990,
        "language": "en",
        "cover_image_url": "https://covers.openlibrary.org/b/id/1-L.jpg",
    }
    defaults.update(overrides)
    return ExternalBookDetail(**defaults)  # type: ignore[arg-type]


@pytest.fixture
def service(db_session: AsyncSession) -> RefreshMetadataService:
    return RefreshMetadataService(
        db_session, ReleaseRepository(db_session), source=_FAKE_SOURCE
    )


class TestRefreshStaleReleases:
    async def test_fills_blank_fields_and_marks_synced(
        self, db_session: AsyncSession, service: RefreshMetadataService
    ):
        release = await _make_release(db_session, isbn_code="9780441013593")
        FakeAdapter.details_by_isbn = {"9780441013593": _detail()}

        summary = await service.refresh_stale_releases(older_than_days=30)

        assert summary.refreshed == 1
        assert summary.conflicts == 0
        assert summary.skipped == 0
        reloaded = await ReleaseRepository(db_session).get_by_id(release.id)
        assert reloaded is not None
        assert reloaded.publisher == "Ace Books"
        assert reloaded.language == "en"
        assert reloaded.cover_image_url == "https://covers.openlibrary.org/b/id/1-L.jpg"
        assert reloaded.last_external_sync_at is not None

    async def test_conflicting_field_is_not_overwritten(
        self, db_session: AsyncSession, service: RefreshMetadataService
    ):
        release = await _make_release(
            db_session, isbn_code="9780441013593", publisher="User Edited Publisher"
        )
        FakeAdapter.details_by_isbn = {"9780441013593": _detail()}

        summary = await service.refresh_stale_releases(older_than_days=30)

        assert summary.refreshed == 1
        assert summary.conflicts == 1
        assert len(summary.conflict_details) == 1
        reloaded = await ReleaseRepository(db_session).get_by_id(release.id)
        assert reloaded is not None
        assert reloaded.publisher == "User Edited Publisher"

    async def test_release_without_matching_external_detail_is_skipped(
        self, db_session: AsyncSession, service: RefreshMetadataService
    ):
        release = await _make_release(db_session, isbn_code="0000000000000")
        FakeAdapter.details_by_isbn = {}

        summary = await service.refresh_stale_releases(older_than_days=30)

        assert summary.skipped == 1
        assert summary.refreshed == 0
        reloaded = await ReleaseRepository(db_session).get_by_id(release.id)
        assert reloaded is not None
        assert reloaded.last_external_sync_at is None

    async def test_release_without_isbn_is_skipped(
        self, db_session: AsyncSession, service: RefreshMetadataService
    ):
        book = Book(title="No ISBN Book", description="desc")
        db_session.add(book)
        await db_session.flush()
        db_session.add(
            Release(
                book_id=book.id,
                format=ReleaseFormat.hardcover,
                publisher="",
                language="",
            )
        )
        await db_session.commit()

        summary = await service.refresh_stale_releases(older_than_days=30)

        assert summary.refreshed == 0
        assert summary.skipped == 0

    async def test_recently_synced_release_is_not_refreshed(
        self, db_session: AsyncSession, service: RefreshMetadataService
    ):
        recent_sync = datetime.now(UTC) - timedelta(days=1)
        await _make_release(
            db_session,
            isbn_code="9780441013593",
            last_external_sync_at=recent_sync,
        )
        FakeAdapter.details_by_isbn = {"9780441013593": _detail()}

        summary = await service.refresh_stale_releases(older_than_days=30)

        assert summary.refreshed == 0
        assert summary.skipped == 0

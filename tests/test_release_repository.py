import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.catalog import ISBN, Book, ISBNKind, Release, ReleaseFormat
from app.repositories.release_repository import ReleaseRepository


async def _make_release(
    db_session: AsyncSession,
    *,
    with_isbn: bool = True,
    last_external_sync_at: datetime | None = None,
) -> Release:
    book = Book(title="Dune", description="Desert planet epic")
    db_session.add(book)
    await db_session.flush()

    release = Release(
        book_id=book.id,
        format=ReleaseFormat.hardcover,
        publisher="Chilton Books",
        language="en",
        last_external_sync_at=last_external_sync_at,
    )
    db_session.add(release)
    await db_session.flush()

    if with_isbn:
        db_session.add(
            ISBN(
                release_id=release.id,
                code_normalized="9780441013593",
                code_original="9780441013593",
                kind=ISBNKind.isbn13,
            )
        )
    await db_session.commit()
    return release


@pytest.fixture
def repository(db_session: AsyncSession) -> ReleaseRepository:
    return ReleaseRepository(db_session)


class TestGetStale:
    async def test_includes_release_never_synced(
        self, db_session: AsyncSession, repository: ReleaseRepository
    ):
        release = await _make_release(db_session, last_external_sync_at=None)

        stale = await repository.get_stale(datetime.now(UTC))

        assert release.id in {r.id for r in stale}

    async def test_includes_release_synced_before_cutoff(
        self, db_session: AsyncSession, repository: ReleaseRepository
    ):
        old_sync = datetime.now(UTC) - timedelta(days=60)
        release = await _make_release(db_session, last_external_sync_at=old_sync)

        stale = await repository.get_stale(datetime.now(UTC) - timedelta(days=30))

        assert release.id in {r.id for r in stale}

    async def test_excludes_release_synced_after_cutoff(
        self, db_session: AsyncSession, repository: ReleaseRepository
    ):
        recent_sync = datetime.now(UTC) - timedelta(days=1)
        release = await _make_release(db_session, last_external_sync_at=recent_sync)

        stale = await repository.get_stale(datetime.now(UTC) - timedelta(days=30))

        assert release.id not in {r.id for r in stale}

    async def test_excludes_release_without_isbn(
        self, db_session: AsyncSession, repository: ReleaseRepository
    ):
        release = await _make_release(
            db_session, with_isbn=False, last_external_sync_at=None
        )

        stale = await repository.get_stale(datetime.now(UTC))

        assert release.id not in {r.id for r in stale}


class TestMarkSynced:
    async def test_sets_last_external_sync_at(
        self, db_session: AsyncSession, repository: ReleaseRepository
    ):
        release = await _make_release(db_session, last_external_sync_at=None)
        synced_at = datetime.now(UTC)

        await repository.mark_synced(release.id, synced_at)

        reloaded = await repository.get_by_id(release.id)
        assert reloaded is not None
        assert reloaded.last_external_sync_at == synced_at

    async def test_unknown_release_id_is_noop(
        self, db_session: AsyncSession, repository: ReleaseRepository
    ):
        await repository.mark_synced(uuid.uuid4(), datetime.now(UTC))

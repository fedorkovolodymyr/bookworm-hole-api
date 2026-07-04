import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.models.external_source import ExternalRefKind
from app.repositories.external_source_repository import ExternalSourceRepository


@pytest.fixture
async def session():
    async for session in get_session():
        yield session


class TestExternalSourceRepository:
    async def test_create_persists_record(self, session: AsyncSession):
        repo = ExternalSourceRepository(session)

        record = await repo.create(
            source="open_library",
            ref_kind=ExternalRefKind.isbn,
            ref="9780441013593",
            payload={"title": "Dune"},
        )

        assert record.id is not None
        assert record.source == "open_library"
        assert record.ref_kind == ExternalRefKind.isbn
        assert record.ref == "9780441013593"
        assert record.payload == {"title": "Dune"}

    async def test_get_by_source_and_ref_returns_latest(self, session: AsyncSession):
        repo = ExternalSourceRepository(session)
        await repo.create(
            source="open_library",
            ref_kind=ExternalRefKind.search,
            ref="dune",
            payload={"title": "old"},
        )
        await repo.create(
            source="open_library",
            ref_kind=ExternalRefKind.search,
            ref="dune",
            payload={"title": "new"},
        )

        record = await repo.get_by_source_and_ref(
            source="open_library", ref_kind=ExternalRefKind.search, ref="dune"
        )

        assert record is not None
        assert record.payload == {"title": "new"}

    async def test_get_by_source_and_ref_returns_none_when_missing(
        self, session: AsyncSession
    ):
        repo = ExternalSourceRepository(session)

        record = await repo.get_by_source_and_ref(
            source="open_library", ref_kind=ExternalRefKind.isbn, ref="missing"
        )

        assert record is None

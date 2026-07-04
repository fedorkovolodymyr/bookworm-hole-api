import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.models.external_source import ExternalRefKind, ExternalSourceRecord
from app.repositories.external_source_repository import ExternalSourceRepository
from app.services.external import (
    AdapterNotFoundError,
    BookSourceAdapter,
    get_adapter,
    register_adapter,
)
from app.services.external.base import ExternalBookDetail
from app.services.external.registry import _registry


@pytest.fixture
async def session():
    async for session in get_session():
        yield session


class FakeAdapter(BookSourceAdapter):
    name = "fake"

    async def search(
        self, query: str, session: AsyncSession
    ) -> list[ExternalSourceRecord]:
        repo = ExternalSourceRepository(session)
        record = await repo.create(
            source=self.name,
            ref_kind=ExternalRefKind.search,
            ref=query,
            payload={"title": f"Result for {query}"},
        )
        return [record]

    async def get_by_isbn(
        self, isbn: str, session: AsyncSession
    ) -> ExternalSourceRecord | None:
        if isbn != "9780134685991":
            return None
        repo = ExternalSourceRepository(session)
        return await repo.create(
            source=self.name,
            ref_kind=ExternalRefKind.isbn,
            ref=isbn,
            payload={"title": "Fake Title"},
        )

    async def get_detail(
        self, source_id: str, session: AsyncSession
    ) -> ExternalBookDetail | None:
        return None


class TestBookSourceAdapter:
    def test_cannot_instantiate_abstract_class(self):
        with pytest.raises(TypeError):
            BookSourceAdapter()  # type: ignore[abstract]

    def test_subclass_missing_method_cannot_instantiate(self):
        class IncompleteAdapter(BookSourceAdapter):
            name = "incomplete"

            async def search(
                self, query: str, session: AsyncSession
            ) -> list[ExternalSourceRecord]:
                return []

        with pytest.raises(TypeError):
            IncompleteAdapter()  # type: ignore[abstract]


class TestFakeAdapter:
    async def test_search_persists_and_returns_records(self, session: AsyncSession):
        adapter = FakeAdapter()
        records = await adapter.search("dune", session)

        assert len(records) == 1
        assert records[0].source == "fake"
        assert records[0].ref_kind == ExternalRefKind.search
        assert records[0].ref == "dune"
        assert records[0].payload == {"title": "Result for dune"}

    async def test_get_by_isbn_persists_and_returns_record(self, session: AsyncSession):
        adapter = FakeAdapter()
        record = await adapter.get_by_isbn("9780134685991", session)

        assert record is not None
        assert record.ref_kind == ExternalRefKind.isbn
        assert record.payload == {"title": "Fake Title"}

    async def test_get_by_isbn_returns_none_for_unknown(self, session: AsyncSession):
        adapter = FakeAdapter()
        record = await adapter.get_by_isbn("0000000000000", session)

        assert record is None


class TestRegistry:
    def setup_method(self):
        register_adapter("fake")(FakeAdapter)

    def teardown_method(self):
        _registry.pop("fake", None)

    def test_get_adapter_returns_registered_instance(self):
        adapter = get_adapter("fake")
        assert isinstance(adapter, FakeAdapter)

    def test_get_adapter_unknown_raises(self):
        with pytest.raises(AdapterNotFoundError):
            get_adapter("does-not-exist")

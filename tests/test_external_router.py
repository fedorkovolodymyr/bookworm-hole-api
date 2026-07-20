import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.catalog import ISBNKind, ReleaseFormat
from app.models.external_source import ExternalRefKind, ExternalSourceRecord
from app.services.external.base import (
    BookSourceAdapter,
    ExternalBookDetail,
    ExternalContributor,
    ExternalISBN,
)
from app.services.external.registry import _registry, register_adapter

_DETAILS: dict[str, ExternalBookDetail | None] = {}
_SEARCH_RESULTS: dict[str, list[ExternalSourceRecord]] = {}


class StubAdapter(BookSourceAdapter):
    name = "stub"

    async def search(
        self, query: str, session: AsyncSession
    ) -> list[ExternalSourceRecord]:
        return _SEARCH_RESULTS.get(query, [])

    async def get_by_isbn(
        self, isbn: str, session: AsyncSession
    ) -> ExternalSourceRecord | None:
        return None

    async def get_detail(
        self, source_id: str, session: AsyncSession
    ) -> ExternalBookDetail | None:
        return _DETAILS.get(source_id)


@pytest.fixture(autouse=True)
def register_stub_adapter():
    register_adapter("stub")(StubAdapter)
    yield
    _registry.pop("stub", None)
    _DETAILS.clear()
    _SEARCH_RESULTS.clear()


class TestImportBookRoute:
    async def test_admin_imports_new_book(self, admin_client: AsyncClient):
        _DETAILS["router-book-a"] = ExternalBookDetail(
            title="Test Router Book A",
            description="desc",
            contributors=[ExternalContributor(full_name="Test Router Author A")],
            isbns=[ExternalISBN(code="9780000010063", kind=ISBNKind.isbn13)],
            format=ReleaseFormat.paperback,
            publisher="Test Publisher",
            published_year=2001,
            language="en",
        )

        response = await admin_client.post(
            "/api/v1/external/import",
            json={"source": "stub", "source_id": "router-book-a"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Test Router Book A"
        assert len(data["releases"]) == 1

    async def test_unauthenticated_returns_401(self, async_client: AsyncClient):
        response = await async_client.post(
            "/api/v1/external/import",
            json={"source": "stub", "source_id": "irrelevant"},
        )
        assert response.status_code == 401

    async def test_reader_forbidden(self, reader_client: AsyncClient):
        response = await reader_client.post(
            "/api/v1/external/import",
            json={"source": "stub", "source_id": "irrelevant"},
        )
        assert response.status_code == 403

    async def test_unknown_source_returns_404(self, admin_client: AsyncClient):
        response = await admin_client.post(
            "/api/v1/external/import",
            json={"source": "does-not-exist", "source_id": "irrelevant"},
        )
        assert response.status_code == 404

    async def test_missing_source_book_returns_404(self, admin_client: AsyncClient):
        response = await admin_client.post(
            "/api/v1/external/import",
            json={"source": "stub", "source_id": "unknown-id"},
        )
        assert response.status_code == 404


class TestSearchRoute:
    async def test_search_returns_hits(self, async_client: AsyncClient):
        record = ExternalSourceRecord(
            source="stub",
            ref_kind=ExternalRefKind.search,
            ref="dune",
            payload={
                "title": "Dune",
                "author_name": "Frank Herbert",
                "isbn_13": ["9780441172719"],
                "isbn_10": [],
                "key": "/works/OL1W",
            },
        )
        _SEARCH_RESULTS["dune"] = [record]

        response = await async_client.get("/api/v1/external/search?q=dune&sources=stub")

        assert response.status_code == 200
        data = response.json()
        assert data["query"] == "dune"
        assert len(data["hits"]) == 1
        assert data["hits"][0]["title"] == "Dune"
        assert data["hits"][0]["authors"] == ["Frank Herbert"]
        assert data["hits"][0]["source"] == "stub"
        assert data["hits"][0]["source_id"] == "/works/OL1W"

    async def test_search_drops_hits_missing_source_id(self, async_client: AsyncClient):
        record = ExternalSourceRecord(
            source="stub",
            ref_kind=ExternalRefKind.search,
            ref="dune",
            payload={
                "title": "Dune",
                "author_name": "Frank Herbert",
                "isbn_13": ["9780441172719"],
                "isbn_10": [],
            },
        )
        _SEARCH_RESULTS["dune"] = [record]

        response = await async_client.get("/api/v1/external/search?q=dune&sources=stub")

        assert response.status_code == 200
        data = response.json()
        assert data["hits"] == []

    async def test_search_multiple_sources(self, async_client: AsyncClient):
        record1 = ExternalSourceRecord(
            source="stub",
            ref_kind=ExternalRefKind.search,
            ref="dune",
            payload={
                "title": "Dune",
                "author_name": "Frank Herbert",
                "isbn_13": ["9780441172719"],
                "isbn_10": [],
                "key": "/works/OL1W",
            },
        )
        _SEARCH_RESULTS["dune"] = [record1]

        response = await async_client.get("/api/v1/external/search?q=dune&sources=stub")

        assert response.status_code == 200
        data = response.json()
        assert data["query"] == "dune"
        assert len(data["hits"]) == 1

    async def test_search_deduplicates_by_isbn(self, async_client: AsyncClient):
        record1 = ExternalSourceRecord(
            source="stub",
            ref_kind=ExternalRefKind.search,
            ref="dune",
            payload={
                "title": "Dune",
                "author_name": "Frank Herbert",
                "isbn_13": ["9780441172719"],
                "isbn_10": [],
                "key": "/works/OL1W",
            },
        )
        record2 = ExternalSourceRecord(
            source="stub",
            ref_kind=ExternalRefKind.search,
            ref="dune",
            payload={
                "title": "Dune",
                "author_name": "Frank Herbert",
                "isbn_13": ["9780441172719"],
                "isbn_10": [],
                "key": "/works/OL1W",
            },
        )
        _SEARCH_RESULTS["dune"] = [record1, record2]

        response = await async_client.get("/api/v1/external/search?q=dune&sources=stub")

        assert response.status_code == 200
        data = response.json()
        assert len(data["hits"]) == 1

    async def test_search_no_partial_failures(self, async_client: AsyncClient):
        record = ExternalSourceRecord(
            source="stub",
            ref_kind=ExternalRefKind.search,
            ref="dune",
            payload={
                "title": "Dune",
                "author_name": "Frank Herbert",
                "isbn_13": ["9780441172719"],
                "isbn_10": [],
                "key": "/works/OL1W",
            },
        )
        _SEARCH_RESULTS["dune"] = [record]

        response = await async_client.get("/api/v1/external/search?q=dune&sources=stub")

        assert response.status_code == 200
        data = response.json()
        assert data["partial_failures"] == {}

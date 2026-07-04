import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.catalog import ISBNKind, ReleaseFormat
from app.models.external_source import ExternalSourceRecord
from app.services.external.base import (
    BookSourceAdapter,
    ExternalBookDetail,
    ExternalContributor,
    ExternalISBN,
)
from app.services.external.registry import _registry, register_adapter

_DETAILS: dict[str, ExternalBookDetail | None] = {}


class StubAdapter(BookSourceAdapter):
    name = "stub"

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
        return _DETAILS.get(source_id)


@pytest.fixture(autouse=True)
def register_stub_adapter():
    register_adapter("stub")(StubAdapter)
    yield
    _registry.pop("stub", None)
    _DETAILS.clear()


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

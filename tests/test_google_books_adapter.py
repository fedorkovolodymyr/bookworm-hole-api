import json
from pathlib import Path

import httpx
import pytest
import respx
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.errors import ExternalServiceError
from app.models.catalog import ISBNKind, ReleaseFormat
from app.models.external_source import ExternalRefKind
from app.services.external import get_adapter
from app.services.external.base import ExternalContributor
from app.services.external.google_books import GoogleBooksAdapter

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "google_books"
BASE_URL = "https://www.googleapis.com/books/v1"


def _load_fixture(name: str) -> dict:
    return json.loads((FIXTURES_DIR / name).read_text())


@pytest.fixture
async def session():
    async for session in get_session():
        yield session


class TestSearch:
    @respx.mock
    async def test_search_persists_raw_items(self, session: AsyncSession):
        respx.get(f"{BASE_URL}/volumes").mock(
            return_value=httpx.Response(200, json=_load_fixture("search_dune.json"))
        )
        adapter = GoogleBooksAdapter()

        records = await adapter.search("dune", session)

        assert len(records) == 1
        record = records[0]
        assert record.source == "google_books"
        assert record.ref_kind == ExternalRefKind.search
        assert record.ref == "dune"
        assert record.payload["id"] == "abc123XYZ"
        assert record.payload["volumeInfo"]["title"] == "Dune"

    @respx.mock
    async def test_search_returns_empty_list_when_no_items(self, session: AsyncSession):
        respx.get(f"{BASE_URL}/volumes").mock(
            return_value=httpx.Response(200, json={"kind": "books#volumes"})
        )
        adapter = GoogleBooksAdapter()

        records = await adapter.search("no-results-query", session)

        assert records == []

    @respx.mock
    async def test_search_raises_external_service_error_on_http_failure(
        self, session: AsyncSession
    ):
        respx.get(f"{BASE_URL}/volumes").mock(return_value=httpx.Response(500))
        adapter = GoogleBooksAdapter()

        with pytest.raises(ExternalServiceError):
            await adapter.search("dune", session)


class TestGetByIsbn:
    @respx.mock
    async def test_persists_first_matching_item(self, session: AsyncSession):
        respx.get(f"{BASE_URL}/volumes", params={"q": "isbn:9780441013593"}).mock(
            return_value=httpx.Response(
                200, json=_load_fixture("isbn_9780441013593.json")
            )
        )
        adapter = GoogleBooksAdapter()

        record = await adapter.get_by_isbn("9780441013593", session)

        assert record is not None
        assert record.source == "google_books"
        assert record.ref_kind == ExternalRefKind.isbn
        assert record.ref == "9780441013593"
        assert record.payload["id"] == "abc123XYZ"

    @respx.mock
    async def test_returns_none_when_no_items(self, session: AsyncSession):
        respx.get(f"{BASE_URL}/volumes", params={"q": "isbn:0000000000000"}).mock(
            return_value=httpx.Response(200, json={"kind": "books#volumes"})
        )
        adapter = GoogleBooksAdapter()

        record = await adapter.get_by_isbn("0000000000000", session)

        assert record is None

    @respx.mock
    async def test_raises_external_service_error_on_http_failure(
        self, session: AsyncSession
    ):
        respx.get(f"{BASE_URL}/volumes", params={"q": "isbn:9780441013593"}).mock(
            return_value=httpx.Response(500)
        )
        adapter = GoogleBooksAdapter()

        with pytest.raises(ExternalServiceError):
            await adapter.get_by_isbn("9780441013593", session)


class TestGetDetail:
    @respx.mock
    async def test_returns_full_detail(self, session: AsyncSession):
        respx.get(f"{BASE_URL}/volumes/abc123XYZ").mock(
            return_value=httpx.Response(
                200, json=_load_fixture("volume_abc123XYZ.json")
            )
        )
        adapter = GoogleBooksAdapter()

        detail = await adapter.get_detail("abc123XYZ", session)

        assert detail is not None
        assert detail.title == "Dune"
        assert detail.description is not None
        assert "Arrakis" in detail.description
        assert detail.contributors == [ExternalContributor(full_name="Frank Herbert")]
        assert {(isbn.code, isbn.kind) for isbn in detail.isbns} == {
            ("9780441013593", ISBNKind.isbn13),
            ("0441013597", ISBNKind.isbn10),
        }
        assert detail.format == ReleaseFormat.ebook
        assert detail.publisher == "Ace Books"
        assert detail.published_year == 1965
        assert detail.language == "en"
        assert detail.cover_image_url == (
            "https://books.google.com/books/content?id=abc123XYZ&img=1&zoom=1"
        )

    @respx.mock
    async def test_returns_none_when_not_found(self, session: AsyncSession):
        respx.get(f"{BASE_URL}/volumes/does-not-exist").mock(
            return_value=httpx.Response(404)
        )
        adapter = GoogleBooksAdapter()

        detail = await adapter.get_detail("does-not-exist", session)

        assert detail is None

    @respx.mock
    async def test_raises_external_service_error_on_http_failure(
        self, session: AsyncSession
    ):
        respx.get(f"{BASE_URL}/volumes/abc123XYZ").mock(
            return_value=httpx.Response(500)
        )
        adapter = GoogleBooksAdapter()

        with pytest.raises(ExternalServiceError):
            await adapter.get_detail("abc123XYZ", session)

    @respx.mock
    async def test_defaults_missing_fields(self, session: AsyncSession):
        respx.get(f"{BASE_URL}/volumes/minimal").mock(
            return_value=httpx.Response(
                200, json={"id": "minimal", "volumeInfo": {"title": "Untitled"}}
            )
        )
        adapter = GoogleBooksAdapter()

        detail = await adapter.get_detail("minimal", session)

        assert detail is not None
        assert detail.title == "Untitled"
        assert detail.description is None
        assert detail.contributors == []
        assert detail.isbns == []
        assert detail.format == ReleaseFormat.other
        assert detail.publisher is None
        assert detail.published_year is None
        assert detail.language is None
        assert detail.cover_image_url is None
        assert detail.genres == []

    @respx.mock
    async def test_maps_categories_to_genres(self, session: AsyncSession):
        respx.get(f"{BASE_URL}/volumes/manga1").mock(
            return_value=httpx.Response(
                200,
                json={
                    "id": "manga1",
                    "volumeInfo": {
                        "title": "Some Manga",
                        "categories": ["Comics & Graphic Novels / Manga / General"],
                    },
                },
            )
        )
        adapter = GoogleBooksAdapter()

        detail = await adapter.get_detail("manga1", session)

        assert detail is not None
        assert set(detail.genres) == {"comics_graphic_novels", "manga"}


class TestRegistry:
    def test_get_adapter_returns_google_books_instance(self):
        adapter = get_adapter("google_books")
        assert isinstance(adapter, GoogleBooksAdapter)

    def test_uses_api_key_when_configured(self):
        adapter = GoogleBooksAdapter()
        adapter._settings.api_key = "test-key"

        params = adapter._params(q="dune")

        assert params == {"q": "dune", "key": "test-key"}

    def test_omits_api_key_when_not_configured(self):
        adapter = GoogleBooksAdapter()
        adapter._settings.api_key = None

        params = adapter._params(q="dune")

        assert params == {"q": "dune"}

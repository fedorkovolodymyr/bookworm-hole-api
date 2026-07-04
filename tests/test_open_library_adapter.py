import json
from pathlib import Path

import httpx
import respx

from app.models.catalog import ISBNKind, ReleaseFormat
from app.services.external import get_adapter
from app.services.external.open_library import OpenLibraryAdapter

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "open_library"


def _load_fixture(name: str) -> dict:
    return json.loads((FIXTURES_DIR / name).read_text())


class TestSearch:
    @respx.mock
    async def test_search_returns_hits(self):
        respx.get("https://openlibrary.org/search.json").mock(
            return_value=httpx.Response(200, json=_load_fixture("search_dune.json"))
        )
        adapter = OpenLibraryAdapter()

        hits = await adapter.search("dune")

        assert len(hits) == 1
        hit = hits[0]
        assert hit.title == "Dune"
        assert hit.contributors[0].full_name == "Frank Herbert"
        assert {i.code for i in hit.isbns} == {"9780441013593", "0441013597"}
        assert (
            hit.cover_image_url == "https://covers.openlibrary.org/b/id/8314396-L.jpg"
        )
        assert hit.raw["key"] == "/works/OL893415W"


class TestGetByIsbn:
    @respx.mock
    async def test_returns_full_detail(self):
        respx.get("https://openlibrary.org/isbn/9780441013593.json").mock(
            return_value=httpx.Response(
                200, json=_load_fixture("isbn_9780441013593.json")
            )
        )
        respx.get("https://openlibrary.org/works/OL893415W.json").mock(
            return_value=httpx.Response(200, json=_load_fixture("work_OL893415W.json"))
        )
        adapter = OpenLibraryAdapter()

        detail = await adapter.get_by_isbn("9780441013593")

        assert detail is not None
        assert detail.title == "Dune"
        assert detail.publisher == "Ace Books"
        assert detail.published_year == 1990
        assert detail.language == "eng"
        assert detail.format == ReleaseFormat.paperback
        assert detail.description is not None
        assert "Arrakis" in detail.description
        assert ISBNKind.isbn13 in {i.kind for i in detail.isbns}
        assert (
            detail.cover_image_url
            == "https://covers.openlibrary.org/b/id/8314396-L.jpg"
        )

    @respx.mock
    async def test_returns_none_when_not_found(self):
        respx.get("https://openlibrary.org/isbn/0000000000000.json").mock(
            return_value=httpx.Response(404)
        )
        adapter = OpenLibraryAdapter()

        detail = await adapter.get_by_isbn("0000000000000")

        assert detail is None


class TestRegistry:
    def test_get_adapter_returns_open_library_instance(self):
        adapter = get_adapter("open_library")
        assert isinstance(adapter, OpenLibraryAdapter)

import json
from pathlib import Path

import httpx
import pytest
import respx
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.models.external_source import ExternalRefKind
from app.services.external import get_adapter
from app.services.external.open_library import OpenLibraryAdapter

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "open_library"


def _load_fixture(name: str) -> dict:
    return json.loads((FIXTURES_DIR / name).read_text())


@pytest.fixture
async def session():
    async for session in get_session():
        yield session


class TestSearch:
    @respx.mock
    async def test_search_persists_raw_docs(self, session: AsyncSession):
        respx.get("https://openlibrary.org/search.json").mock(
            return_value=httpx.Response(200, json=_load_fixture("search_dune.json"))
        )
        adapter = OpenLibraryAdapter()

        records = await adapter.search("dune", session)

        assert len(records) == 1
        record = records[0]
        assert record.source == "open_library"
        assert record.ref_kind == ExternalRefKind.search
        assert record.ref == "dune"
        assert record.payload["title"] == "Dune"
        assert record.payload["author_name"] == ["Frank Herbert"]
        assert record.payload["key"] == "/works/OL893415W"


class TestGetByIsbn:
    @respx.mock
    async def test_persists_isbn_and_work_doc(self, session: AsyncSession):
        respx.get("https://openlibrary.org/isbn/9780441013593.json").mock(
            return_value=httpx.Response(
                200, json=_load_fixture("isbn_9780441013593.json")
            )
        )
        respx.get("https://openlibrary.org/works/OL893415W.json").mock(
            return_value=httpx.Response(200, json=_load_fixture("work_OL893415W.json"))
        )
        adapter = OpenLibraryAdapter()

        record = await adapter.get_by_isbn("9780441013593", session)

        assert record is not None
        assert record.source == "open_library"
        assert record.ref_kind == ExternalRefKind.isbn
        assert record.ref == "9780441013593"
        assert record.payload["isbn_doc"]["title"] == "Dune"
        assert "Arrakis" in record.payload["work_doc"]["description"]["value"]

    @respx.mock
    async def test_returns_none_when_not_found(self, session: AsyncSession):
        respx.get("https://openlibrary.org/isbn/0000000000000.json").mock(
            return_value=httpx.Response(404)
        )
        adapter = OpenLibraryAdapter()

        record = await adapter.get_by_isbn("0000000000000", session)

        assert record is None


class TestGetDetail:
    @respx.mock
    async def test_by_work_key_uses_work_endpoint_not_isbn_endpoint(
        self, session: AsyncSession
    ):
        respx.get("https://openlibrary.org/works/OL893415W.json").mock(
            return_value=httpx.Response(200, json=_load_fixture("work_OL893415W.json"))
        )
        adapter = OpenLibraryAdapter()

        detail = await adapter.get_detail("/works/OL893415W", session)

        assert detail is not None
        assert detail.title == "Dune"
        assert detail.description is not None
        assert "Arrakis" in detail.description
        assert (
            detail.cover_image_url
            == "https://covers.openlibrary.org/b/id/8314396-L.jpg"
        )
        assert detail.isbns == []
        assert detail.contributors == []
        assert detail.genres == []

    @respx.mock
    async def test_by_work_key_maps_subjects_to_genres(self, session: AsyncSession):
        respx.get("https://openlibrary.org/works/OL893415W.json").mock(
            return_value=httpx.Response(
                200,
                json={
                    "title": "Dune",
                    "subjects": ["Science fiction", "Fantasy fiction"],
                },
            )
        )
        adapter = OpenLibraryAdapter()

        detail = await adapter.get_detail("/works/OL893415W", session)

        assert detail is not None
        assert set(detail.genres) == {
            "science_fiction",
            "science",
            "fantasy",
            "fiction",
        }

    @respx.mock
    async def test_by_work_key_returns_none_when_not_found(self, session: AsyncSession):
        respx.get("https://openlibrary.org/works/OL0000000W.json").mock(
            return_value=httpx.Response(404)
        )
        adapter = OpenLibraryAdapter()

        detail = await adapter.get_detail("/works/OL0000000W", session)

        assert detail is None

    @respx.mock
    async def test_by_isbn_falls_back_to_isbn_endpoint(self, session: AsyncSession):
        respx.get("https://openlibrary.org/isbn/9780441013593.json").mock(
            return_value=httpx.Response(
                200, json=_load_fixture("isbn_9780441013593.json")
            )
        )
        respx.get("https://openlibrary.org/works/OL893415W.json").mock(
            return_value=httpx.Response(200, json=_load_fixture("work_OL893415W.json"))
        )
        adapter = OpenLibraryAdapter()

        detail = await adapter.get_detail("9780441013593", session)

        assert detail is not None
        assert detail.title == "Dune"


class TestRegistry:
    def test_get_adapter_returns_open_library_instance(self):
        adapter = get_adapter("open_library")
        assert isinstance(adapter, OpenLibraryAdapter)

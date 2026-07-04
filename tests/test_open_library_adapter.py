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


class TestRegistry:
    def test_get_adapter_returns_open_library_instance(self):
        adapter = get_adapter("open_library")
        assert isinstance(adapter, OpenLibraryAdapter)

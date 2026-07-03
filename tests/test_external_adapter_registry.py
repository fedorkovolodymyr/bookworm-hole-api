import pytest

from app.models.catalog import ISBNKind, ReleaseFormat
from app.services.external import (
    AdapterNotFoundError,
    BookSourceAdapter,
    ExternalBookDetail,
    ExternalBookHit,
    ExternalContributor,
    ExternalISBN,
    get_adapter,
    register_adapter,
)
from app.services.external.registry import _registry


class FakeAdapter(BookSourceAdapter):
    name = "fake"

    async def search(self, query: str) -> list[ExternalBookHit]:
        return [
            ExternalBookHit(
                title=f"Result for {query}",
                contributors=[ExternalContributor(full_name="Jane Doe")],
                isbns=[ExternalISBN(code="9780134685991", kind=ISBNKind.isbn13)],
                raw={"source_id": "abc123"},
            )
        ]

    async def get_by_isbn(self, isbn: str) -> ExternalBookDetail | None:
        if isbn != "9780134685991":
            return None
        return ExternalBookDetail(
            title="Fake Title",
            description="A fake book.",
            contributors=[ExternalContributor(full_name="Jane Doe")],
            isbns=[ExternalISBN(code=isbn, kind=ISBNKind.isbn13)],
            format=ReleaseFormat.paperback,
            publisher="Fake Press",
            published_year=2020,
            language="en",
            raw={"source_id": "abc123"},
        )


class TestBookSourceAdapter:
    def test_cannot_instantiate_abstract_class(self):
        with pytest.raises(TypeError):
            BookSourceAdapter()  # type: ignore[abstract]

    def test_subclass_missing_method_cannot_instantiate(self):
        class IncompleteAdapter(BookSourceAdapter):
            name = "incomplete"

            async def search(self, query: str) -> list[ExternalBookHit]:
                return []

        with pytest.raises(TypeError):
            IncompleteAdapter()  # type: ignore[abstract]


class TestFakeAdapter:
    async def test_search_returns_hits(self):
        adapter = FakeAdapter()
        hits = await adapter.search("dune")

        assert len(hits) == 1
        assert hits[0].title == "Result for dune"
        assert hits[0].raw == {"source_id": "abc123"}

    async def test_get_by_isbn_returns_detail(self):
        adapter = FakeAdapter()
        detail = await adapter.get_by_isbn("9780134685991")

        assert detail is not None
        assert detail.title == "Fake Title"
        assert detail.publisher == "Fake Press"

    async def test_get_by_isbn_returns_none_for_unknown(self):
        adapter = FakeAdapter()
        detail = await adapter.get_by_isbn("0000000000000")

        assert detail is None


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

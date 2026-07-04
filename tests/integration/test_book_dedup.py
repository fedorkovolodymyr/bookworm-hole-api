import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError
from app.models.catalog import ContributorRole, ISBNKind, ReleaseFormat
from app.models.external_source import ExternalSourceRecord
from app.repositories.book_repository import BookRepository
from app.repositories.contributor_repository import ContributorRepository
from app.repositories.import_repository import ImportRepository
from app.services.external.base import (
    BookSourceAdapter,
    ExternalBookDetail,
    ExternalContributor,
    ExternalISBN,
)
from app.services.external.registry import _registry, register_adapter
from app.services.import_service import ImportService

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


@pytest.fixture
def import_service(db_session: AsyncSession) -> ImportService:
    return ImportService(
        db_session,
        BookRepository(db_session),
        ContributorRepository(db_session),
        ImportRepository(db_session),
    )


def _detail(*, title: str, isbn_code: str, author: str) -> ExternalBookDetail:
    return ExternalBookDetail(
        title=title,
        description="A test description",
        contributors=[
            ExternalContributor(full_name=author, role=ContributorRole.author)
        ],
        isbns=[ExternalISBN(code=isbn_code, kind=ISBNKind.isbn13)],
        format=ReleaseFormat.paperback,
        publisher="Test Publisher",
        published_year=2000,
        language="en",
    )


class TestImportBookDedup:
    async def test_existing_isbn_returns_existing_book_no_duplicate(
        self, import_service: ImportService
    ):
        _DETAILS["book-b"] = _detail(
            title="Test Import Book B",
            isbn_code="9780000010018",
            author="Test Author B",
        )

        first = await import_service.import_book("stub", "book-b")
        second = await import_service.import_book("stub", "book-b")

        assert second.id == first.id
        assert len(second.releases) == 1

    async def test_new_edition_attaches_release_to_existing_book(
        self, import_service: ImportService
    ):
        _DETAILS["book-c-hardcover"] = _detail(
            title="Test Import Book C",
            isbn_code="9780000010025",
            author="Test Author C",
        )
        hardcover = await import_service.import_book("stub", "book-c-hardcover")

        _DETAILS["book-c-paperback"] = _detail(
            title="Test Import Book C",
            isbn_code="9780000010032",
            author="Test Author C",
        )
        paperback = await import_service.import_book("stub", "book-c-paperback")

        assert paperback.id == hardcover.id
        assert len(paperback.releases) == 2

    async def test_contributor_reused_by_name_match(
        self, import_service: ImportService, db_session: AsyncSession
    ):
        contributor_repo = ContributorRepository(db_session)
        existing = await contributor_repo.add("Test Author D", "D, Test Author")

        _DETAILS["book-d"] = _detail(
            title="Test Import Book D",
            isbn_code="9780000010049",
            author="Test Author D",
        )
        book = await import_service.import_book("stub", "book-d")

        assert len(book.contributors) == 1
        assert book.contributors[0].id == existing.id

    async def test_idempotent_reimport_same_ids(self, import_service: ImportService):
        _DETAILS["book-e"] = _detail(
            title="Test Import Book E",
            isbn_code="9780000010056",
            author="Test Author E",
        )

        first = await import_service.import_book("stub", "book-e")
        first_release_id = first.releases[0].id
        first_contributor_id = first.contributors[0].id

        second = await import_service.import_book("stub", "book-e")

        assert second.id == first.id
        assert second.releases[0].id == first_release_id
        assert second.contributors[0].id == first_contributor_id

    async def test_search_by_any_isbn_resolves_to_canonical_book(
        self, import_service: ImportService, db_session: AsyncSession
    ):
        _DETAILS["book-f-hardcover"] = _detail(
            title="Test Import Book F",
            isbn_code="9780000010063",
            author="Test Author F",
        )
        hardcover = await import_service.import_book("stub", "book-f-hardcover")

        _DETAILS["book-f-paperback"] = _detail(
            title="Test Import Book F",
            isbn_code="9780000010070",
            author="Test Author F",
        )
        await import_service.import_book("stub", "book-f-paperback")

        book_repo = BookRepository(db_session)
        by_hardcover_isbn = await book_repo.get_by_isbn("9780000010063")
        by_paperback_isbn = await book_repo.get_by_isbn("9780000010070")

        assert by_hardcover_isbn is not None
        assert by_paperback_isbn is not None
        assert by_hardcover_isbn.id == hardcover.id
        assert by_paperback_isbn.id == hardcover.id

    async def test_unknown_source_raises_404(self, import_service: ImportService):
        with pytest.raises(NotFoundError) as exc_info:
            await import_service.import_book("does-not-exist", "irrelevant")
        assert exc_info.value.status_code == 404

    async def test_missing_source_book_raises_404(self, import_service: ImportService):
        with pytest.raises(NotFoundError) as exc_info:
            await import_service.import_book("stub", "unknown-id")
        assert exc_info.value.status_code == 404

import pytest
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col, delete, select

from app.core.db import get_session
from app.core.errors import NotFoundError
from app.models.catalog import (
    ISBN,
    Book,
    BookContributor,
    Contributor,
    ContributorRole,
    ISBNKind,
    Release,
    ReleaseContributor,
    ReleaseFormat,
)
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
async def session():
    async for session in get_session():
        yield session


@pytest.fixture
def import_service(session: AsyncSession) -> ImportService:
    return ImportService(
        session,
        BookRepository(session),
        ContributorRepository(session),
        ImportRepository(session),
    )


@pytest.fixture
async def cleanup():
    book_ids: list = []
    contributor_ids: list = []
    yield book_ids, contributor_ids
    try:
        async for session in get_session():
            if book_ids:
                release_ids = (
                    (
                        await session.execute(
                            select(Release.id).where(col(Release.book_id).in_(book_ids))
                        )
                    )
                    .scalars()
                    .all()
                )
                if release_ids:
                    await session.execute(
                        delete(ISBN).where(col(ISBN.release_id).in_(release_ids))
                    )
                    await session.execute(
                        delete(ReleaseContributor).where(
                            col(ReleaseContributor.release_id).in_(release_ids)
                        )
                    )
                    await session.execute(
                        delete(Release).where(col(Release.id).in_(release_ids))
                    )
                await session.execute(
                    delete(BookContributor).where(
                        col(BookContributor.book_id).in_(book_ids)
                    )
                )
                await session.execute(delete(Book).where(col(Book.id).in_(book_ids)))
            if contributor_ids:
                await session.execute(
                    delete(Contributor).where(col(Contributor.id).in_(contributor_ids))
                )
            await session.commit()
    except (SQLAlchemyError, OSError) as exc:
        pytest.skip(f"database unavailable: {exc}")


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


class TestImportBook:
    async def test_creates_new_book_release_and_contributor(
        self, import_service: ImportService, cleanup, session: AsyncSession
    ):
        book_ids, contributor_ids = cleanup
        _DETAILS["book-a"] = _detail(
            title="Test Import Book A",
            isbn_code="9780000010001",
            author="Test Author A",
        )

        book = await import_service.import_book("stub", "book-a")
        await session.commit()
        book_ids.append(book.id)
        contributor_ids.extend(c.id for c in book.contributors)

        assert book.title == "Test Import Book A"
        assert len(book.releases) == 1
        assert book.releases[0].isbns[0].code_normalized == "9780000010001"
        assert book.releases[0].publisher == "Test Publisher"
        assert [c.full_name for c in book.contributors] == ["Test Author A"]

    async def test_existing_isbn_returns_existing_book_no_duplicate(
        self, import_service: ImportService, cleanup, session: AsyncSession
    ):
        book_ids, contributor_ids = cleanup
        _DETAILS["book-b"] = _detail(
            title="Test Import Book B",
            isbn_code="9780000010018",
            author="Test Author B",
        )

        first = await import_service.import_book("stub", "book-b")
        await session.commit()
        book_ids.append(first.id)
        contributor_ids.extend(c.id for c in first.contributors)

        second = await import_service.import_book("stub", "book-b")
        await session.commit()

        assert second.id == first.id
        assert len(second.releases) == 1

    async def test_new_edition_attaches_release_to_existing_book(
        self, import_service: ImportService, cleanup, session: AsyncSession
    ):
        book_ids, contributor_ids = cleanup
        _DETAILS["book-c-hardcover"] = _detail(
            title="Test Import Book C",
            isbn_code="9780000010025",
            author="Test Author C",
        )
        hardcover = await import_service.import_book("stub", "book-c-hardcover")
        await session.commit()
        book_ids.append(hardcover.id)
        contributor_ids.extend(c.id for c in hardcover.contributors)

        _DETAILS["book-c-paperback"] = _detail(
            title="Test Import Book C",
            isbn_code="9780000010032",
            author="Test Author C",
        )
        paperback = await import_service.import_book("stub", "book-c-paperback")
        await session.commit()

        assert paperback.id == hardcover.id
        assert len(paperback.releases) == 2

    async def test_contributor_reused_by_name_match(
        self, import_service: ImportService, cleanup, session: AsyncSession
    ):
        book_ids, contributor_ids = cleanup
        contributor_repo = ContributorRepository(session)
        existing = await contributor_repo.add("Test Author D", "D, Test Author")
        await session.commit()
        contributor_ids.append(existing.id)

        _DETAILS["book-d"] = _detail(
            title="Test Import Book D",
            isbn_code="9780000010049",
            author="Test Author D",
        )
        book = await import_service.import_book("stub", "book-d")
        await session.commit()
        book_ids.append(book.id)

        assert len(book.contributors) == 1
        assert book.contributors[0].id == existing.id

    async def test_idempotent_reimport_same_ids(
        self, import_service: ImportService, cleanup, session: AsyncSession
    ):
        book_ids, contributor_ids = cleanup
        _DETAILS["book-e"] = _detail(
            title="Test Import Book E",
            isbn_code="9780000010056",
            author="Test Author E",
        )

        first = await import_service.import_book("stub", "book-e")
        await session.commit()
        book_ids.append(first.id)
        contributor_ids.extend(c.id for c in first.contributors)
        first_release_id = first.releases[0].id
        first_contributor_id = first.contributors[0].id

        second = await import_service.import_book("stub", "book-e")
        await session.commit()

        assert second.id == first.id
        assert second.releases[0].id == first_release_id
        assert second.contributors[0].id == first_contributor_id

    async def test_unknown_source_raises_404(self, import_service: ImportService):
        with pytest.raises(NotFoundError) as exc_info:
            await import_service.import_book("does-not-exist", "irrelevant")
        assert exc_info.value.status_code == 404

    async def test_missing_source_book_raises_404(self, import_service: ImportService):
        with pytest.raises(NotFoundError) as exc_info:
            await import_service.import_book("stub", "unknown-id")
        assert exc_info.value.status_code == 404

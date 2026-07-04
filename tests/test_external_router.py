import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col, delete, select

from app.core.db import get_session
from app.core.deps import get_current_user
from app.main import app
from app.models.catalog import (
    ISBN,
    Book,
    BookContributor,
    Contributor,
    ISBNKind,
    Release,
    ReleaseContributor,
    ReleaseFormat,
)
from app.models.external_source import ExternalSourceRecord
from app.models.user import User
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


@pytest.fixture
async def admin_client():
    admin = User(
        email="admin@example.com", username="admin", display_name="Admin", is_admin=True
    )
    app.dependency_overrides[get_current_user] = lambda: admin
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.fixture
async def reader_client():
    reader = User(email="reader@example.com", username="reader", display_name="Reader")
    app.dependency_overrides[get_current_user] = lambda: reader
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac
    app.dependency_overrides.clear()


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


class TestImportBookRoute:
    async def test_admin_imports_new_book(self, admin_client: AsyncClient, cleanup):
        book_ids, _contributor_ids = cleanup
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
        book_ids.append(data["id"])
        assert data["title"] == "Test Router Book A"
        assert len(data["releases"]) == 1

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

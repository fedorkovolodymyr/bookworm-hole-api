from datetime import UTC, datetime

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import col, delete

from app.core.db import get_session
from app.core.deps import get_current_user
from app.main import app
from app.models.catalog import ISBN, ISBNKind, Release, ReleaseFormat
from app.models.catalog import Book as BookModel
from app.models.user import User


@pytest.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac


@pytest.fixture
async def book_with_releases():
    try:
        async for session in get_session():
            book = BookModel(title="Dune", description="Desert planet epic")
            session.add(book)
            await session.flush()

            hardcover = Release(
                book_id=book.id,
                format=ReleaseFormat.hardcover,
                publisher="Chilton Books",
                language="en",
            )
            paperback = Release(
                book_id=book.id,
                format=ReleaseFormat.paperback,
                publisher="Ace Books",
                language="en",
            )
            session.add(hardcover)
            session.add(paperback)
            await session.flush()

            hardcover_isbn = ISBN(
                release_id=hardcover.id,
                code_normalized="9780441013593",
                code_original="0441013597",
                kind=ISBNKind.isbn13,
                created_at=datetime.now(UTC),
            )
            paperback_isbn = ISBN(
                release_id=paperback.id,
                code_normalized="9780143111580",
                code_original="9780143111580",
                kind=ISBNKind.isbn13,
                created_at=datetime.now(UTC),
            )
            session.add(hardcover_isbn)
            session.add(paperback_isbn)
            await session.commit()

            yield book, hardcover_isbn, paperback_isbn

            await session.execute(
                delete(ISBN).where(
                    col(ISBN.release_id).in_([hardcover.id, paperback.id])
                )
            )
            await session.execute(
                delete(Release).where(col(Release.id).in_([hardcover.id, paperback.id]))
            )
            await session.execute(delete(BookModel).where(col(BookModel.id) == book.id))
            await session.commit()
    except (SQLAlchemyError, OSError) as exc:
        pytest.skip(f"database unavailable: {exc}")


async def test_retrieve_book_by_isbn_dedup_and_shape(
    client: AsyncClient, book_with_releases
):
    book, hardcover_isbn, paperback_isbn = book_with_releases

    response_hc = await client.get(
        f"/api/v1/books/by-isbn/{hardcover_isbn.code_original}"
    )
    response_pb = await client.get(
        f"/api/v1/books/by-isbn/{paperback_isbn.code_original}"
    )

    assert response_hc.status_code == 200
    assert response_pb.status_code == 200
    data = response_hc.json()
    assert data["id"] == str(book.id)
    assert response_pb.json()["id"] == str(book.id)
    assert len(data["releases"]) == 2
    assert all(len(release["isbns"]) == 1 for release in data["releases"])


async def test_retrieve_book_by_isbn_not_found(client: AsyncClient):
    response = await client.get("/api/v1/books/by-isbn/9999999999999")
    assert response.status_code == 404


async def test_retrieve_book_by_isbn_invalid_input(client: AsyncClient):
    response = await client.get("/api/v1/books/by-isbn/not-an-isbn")
    assert response.status_code == 404


async def test_retrieve_book_by_id_includes_releases(
    client: AsyncClient, book_with_releases
):
    book, _, _ = book_with_releases

    response = await client.get(f"/api/v1/books/{book.id}")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(book.id)
    assert len(data["releases"]) == 2


async def test_retrieve_book_by_id_not_found(client: AsyncClient):
    response = await client.get("/api/v1/books/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404


async def test_retrieve_all_books_filters_by_title(
    client: AsyncClient, book_with_releases
):
    book, _, _ = book_with_releases

    response = await client.get("/api/v1/books/", params={"title": "Dune"})

    assert response.status_code == 200
    data = response.json()
    assert {"items", "total", "limit", "offset"} <= data.keys()
    assert any(item["id"] == str(book.id) for item in data["items"])


async def test_create_book_requires_admin(client: AsyncClient):
    response = await client.post(
        "/api/v1/books/",
        json={"title": "New Book", "description": "desc"},
    )
    assert response.status_code == 401


async def test_create_book_forbidden_for_non_admin(client: AsyncClient):
    reader = User(email="reader@example.com", username="reader", display_name="Reader")
    app.dependency_overrides[get_current_user] = lambda: reader
    try:
        response = await client.post(
            "/api/v1/books/",
            json={"title": "New Book", "description": "desc"},
        )
        assert response.status_code == 403
    finally:
        app.dependency_overrides.clear()


async def test_create_book_allowed_for_admin(client: AsyncClient):
    admin = User(
        email="admin@example.com",
        username="admin",
        display_name="Admin",
        is_admin=True,
    )
    app.dependency_overrides[get_current_user] = lambda: admin
    response = None
    try:
        response = await client.post(
            "/api/v1/books/",
            json={"title": "New Book", "description": "desc"},
        )
        assert response.status_code == 201
    finally:
        app.dependency_overrides.clear()
        if response is not None:
            async for session in get_session():
                await session.execute(
                    delete(BookModel).where(col(BookModel.id) == response.json()["id"])
                )
                await session.commit()


async def test_modify_book_requires_admin(client: AsyncClient, book_with_releases):
    book, _, _ = book_with_releases

    response = await client.patch(f"/api/v1/books/{book.id}", json={"title": "Renamed"})
    assert response.status_code == 401


async def test_modify_book_allowed_for_admin(client: AsyncClient, book_with_releases):
    book, _, _ = book_with_releases
    admin = User(
        email="admin@example.com",
        username="admin",
        display_name="Admin",
        is_admin=True,
    )
    app.dependency_overrides[get_current_user] = lambda: admin
    try:
        response = await client.patch(
            f"/api/v1/books/{book.id}", json={"title": "Renamed"}
        )
        assert response.status_code == 200
        assert response.json()["title"] == "Renamed"
    finally:
        app.dependency_overrides.clear()


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("title", "New Title"),
        ("original_title", "Original"),
        ("original_language", "fr"),
        ("first_publication_year", 1965),
        ("description", "New description"),
    ],
)
async def test_modify_book_updates_each_field(
    client: AsyncClient, book_with_releases, field: str, value: object
):
    book, _, _ = book_with_releases
    admin = User(
        email="admin@example.com",
        username="admin",
        display_name="Admin",
        is_admin=True,
    )
    app.dependency_overrides[get_current_user] = lambda: admin
    try:
        response = await client.patch(f"/api/v1/books/{book.id}", json={field: value})
        assert response.status_code == 200
        data = response.json()
        original = {
            "title": book.title,
            "original_title": book.original_title,
            "original_language": book.original_language,
            "first_publication_year": book.first_publication_year,
            "description": book.description,
        }
        for name, original_value in original.items():
            assert data[name] == (value if name == field else original_value)
    finally:
        app.dependency_overrides.clear()

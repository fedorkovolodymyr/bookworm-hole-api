import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import col, delete

from app.core.db import get_session
from app.core.deps import get_current_user
from app.main import app
from app.models.catalog import ISBN, Release, ReleaseFormat
from app.models.catalog import Book as BookModel
from app.models.user import User


@pytest.fixture
async def client():
    admin = User(
        email="admin@example.com",
        username="admin",
        display_name="Admin",
        is_admin=True,
    )
    app.dependency_overrides[get_current_user] = lambda: admin
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.fixture
async def book_with_release():
    try:
        async for session in get_session():
            book = BookModel(title="Dune", description="Desert planet epic")
            session.add(book)
            await session.flush()

            release = Release(
                book_id=book.id,
                format=ReleaseFormat.hardcover,
                publisher="Chilton Books",
                language="en",
            )
            session.add(release)
            await session.commit()

            yield book, release

            await session.execute(
                delete(ISBN).where(col(ISBN.release_id) == release.id)
            )
            await session.execute(delete(Release).where(col(Release.id) == release.id))
            await session.execute(delete(BookModel).where(col(BookModel.id) == book.id))
            await session.commit()
    except (SQLAlchemyError, OSError) as exc:
        pytest.skip(f"database unavailable: {exc}")


async def test_retrieve_release_by_id(client: AsyncClient, book_with_release):
    _, release = book_with_release

    response = await client.get(f"/api/v1/releases/{release.id}")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(release.id)
    assert data["isbns"] == []


async def test_retrieve_release_by_id_not_found(client: AsyncClient):
    response = await client.get("/api/v1/releases/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404


async def test_create_release_for_book(client: AsyncClient, book_with_release):
    book, _ = book_with_release

    response = await client.post(
        "/api/v1/releases/",
        json={
            "book_id": str(book.id),
            "format": "paperback",
            "publisher": "Ace Books",
            "language": "en",
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["publisher"] == "Ace Books"

    async for session in get_session():
        await session.execute(delete(Release).where(col(Release.id) == data["id"]))
        await session.commit()


async def test_create_release_book_not_found(client: AsyncClient):
    response = await client.post(
        "/api/v1/releases/",
        json={
            "book_id": "00000000-0000-0000-0000-000000000000",
            "format": "paperback",
            "publisher": "Ace Books",
            "language": "en",
        },
    )
    assert response.status_code == 404


async def test_modify_release(client: AsyncClient, book_with_release):
    _, release = book_with_release

    response = await client.patch(
        f"/api/v1/releases/{release.id}", json={"publisher": "New Publisher"}
    )

    assert response.status_code == 200
    assert response.json()["publisher"] == "New Publisher"


async def test_modify_release_not_found(client: AsyncClient):
    response = await client.patch(
        "/api/v1/releases/00000000-0000-0000-0000-000000000000",
        json={"publisher": "New Publisher"},
    )
    assert response.status_code == 404


async def test_create_release_requires_admin():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.post(
            "/api/v1/releases/",
            json={
                "book_id": "00000000-0000-0000-0000-000000000000",
                "format": "paperback",
                "publisher": "Ace Books",
                "language": "en",
            },
        )
    assert response.status_code == 401


async def test_modify_release_requires_admin():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.patch(
            "/api/v1/releases/00000000-0000-0000-0000-000000000000",
            json={"publisher": "New Publisher"},
        )
    assert response.status_code == 401

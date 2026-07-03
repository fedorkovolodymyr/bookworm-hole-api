import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import col, delete

from app.core.db import get_session
from app.core.deps import get_current_user
from app.main import app
from app.models.book_status import BookStatus
from app.models.catalog import Book as BookModel
from app.models.user import User


@pytest.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac
    app.dependency_overrides.clear()


async def _persist_user(email: str, username: str, display_name: str) -> User:
    async for session in get_session():
        user = User(email=email, username=username, display_name=display_name)
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user
    raise RuntimeError("no session")


def _login_as(user: User) -> None:
    app.dependency_overrides[get_current_user] = lambda: user


@pytest.fixture
async def owner(client: AsyncClient):
    owner = await _persist_user("owner@example.com", "owner", "Owner")
    _login_as(owner)
    yield owner
    async for session in get_session():
        await session.execute(delete(User).where(col(User.id) == owner.id))
        await session.commit()


@pytest.fixture
async def other(client: AsyncClient):
    other = await _persist_user("other@example.com", "other", "Other")
    yield other
    async for session in get_session():
        await session.execute(delete(User).where(col(User.id) == other.id))
        await session.commit()


@pytest.fixture
async def book():
    try:
        async for session in get_session():
            book = BookModel(title="Dune", description="Desert planet epic")
            session.add(book)
            await session.commit()
            await session.refresh(book)

            yield book

            await session.execute(delete(BookModel).where(col(BookModel.id) == book.id))
            await session.commit()
    except (SQLAlchemyError, OSError) as exc:
        pytest.skip(f"database unavailable: {exc}")


async def _cleanup_status(status_id):
    async for session in get_session():
        await session.execute(delete(BookStatus).where(col(BookStatus.id) == status_id))
        await session.commit()


class TestCreateStatus:
    async def test_requires_auth(self, client: AsyncClient, book):
        response = await client.post(
            "/api/v1/me/statuses/", json={"book_id": str(book.id), "status": "owned"}
        )
        assert response.status_code == 401

    async def test_creates_status(self, client: AsyncClient, owner: User, book):
        response = await client.post(
            "/api/v1/me/statuses/",
            json={"book_id": str(book.id), "status": "owned", "notes": "hardcover"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["user_id"] == str(owner.id)
        assert data["book_id"] == str(book.id)
        assert data["release_id"] is None
        assert data["status"] == "owned"
        assert data["notes"] == "hardcover"
        assert data["acquired_at"] is not None
        await _cleanup_status(data["id"])

    async def test_requires_exactly_one_target(
        self, client: AsyncClient, owner: User, book
    ):
        response = await client.post("/api/v1/me/statuses/", json={"status": "owned"})
        assert response.status_code == 422


class TestListStatuses:
    async def test_filters_by_status_and_owner(
        self, client: AsyncClient, owner: User, other: User, book
    ):
        owned = await client.post(
            "/api/v1/me/statuses/", json={"book_id": str(book.id), "status": "owned"}
        )
        wishlist = await client.post(
            "/api/v1/me/statuses/", json={"book_id": str(book.id), "status": "wishlist"}
        )

        response = await client.get("/api/v1/me/statuses/", params={"status": "owned"})
        assert response.status_code == 200
        data = response.json()
        assert {item["id"] for item in data} == {owned.json()["id"]}

        _login_as(other)
        other_response = await client.get("/api/v1/me/statuses/")
        assert other_response.json() == []

        await _cleanup_status(owned.json()["id"])
        await _cleanup_status(wishlist.json()["id"])


class TestModifyStatus:
    async def test_updates_status(self, client: AsyncClient, owner: User, book):
        created = await client.post(
            "/api/v1/me/statuses/", json={"book_id": str(book.id), "status": "wishlist"}
        )
        status_id = created.json()["id"]

        response = await client.patch(
            f"/api/v1/me/statuses/{status_id}", json={"status": "owned"}
        )
        assert response.status_code == 200
        assert response.json()["status"] == "owned"

        await _cleanup_status(status_id)

    async def test_not_found_for_non_owner(
        self, client: AsyncClient, owner: User, other: User, book
    ):
        created = await client.post(
            "/api/v1/me/statuses/", json={"book_id": str(book.id), "status": "owned"}
        )
        status_id = created.json()["id"]

        _login_as(other)
        response = await client.patch(
            f"/api/v1/me/statuses/{status_id}", json={"status": "sold"}
        )
        assert response.status_code == 404

        await _cleanup_status(status_id)


class TestDeleteStatus:
    async def test_deletes_status(self, client: AsyncClient, owner: User, book):
        created = await client.post(
            "/api/v1/me/statuses/", json={"book_id": str(book.id), "status": "owned"}
        )
        status_id = created.json()["id"]

        response = await client.delete(f"/api/v1/me/statuses/{status_id}")
        assert response.status_code == 204

        follow_up = await client.patch(
            f"/api/v1/me/statuses/{status_id}", json={"status": "sold"}
        )
        assert follow_up.status_code == 404


class TestLendAndReturn:
    async def test_lend_marks_lent_out(self, client: AsyncClient, owner: User, book):
        created = await client.post(
            "/api/v1/me/statuses/", json={"book_id": str(book.id), "status": "owned"}
        )
        status_id = created.json()["id"]

        response = await client.post(
            f"/api/v1/me/statuses/{status_id}/lend",
            json={"lent_to_name": "Alice"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "lent_out"
        assert data["lent_to_name"] == "Alice"
        assert data["lent_at"] is not None
        assert data["returned_at"] is None

        await _cleanup_status(status_id)

    async def test_return_reverts_to_owned(
        self, client: AsyncClient, owner: User, book
    ):
        created = await client.post(
            "/api/v1/me/statuses/", json={"book_id": str(book.id), "status": "owned"}
        )
        status_id = created.json()["id"]
        await client.post(
            f"/api/v1/me/statuses/{status_id}/lend", json={"lent_to_name": "Alice"}
        )

        response = await client.post(f"/api/v1/me/statuses/{status_id}/return")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "owned"
        assert data["returned_at"] is not None
        assert data["lent_to_name"] is None
        assert data["lent_to_user_id"] is None

        await _cleanup_status(status_id)

    async def test_lend_requires_exactly_one_target(
        self, client: AsyncClient, owner: User, book
    ):
        created = await client.post(
            "/api/v1/me/statuses/", json={"book_id": str(book.id), "status": "owned"}
        )
        status_id = created.json()["id"]

        response = await client.post(
            f"/api/v1/me/statuses/{status_id}/lend",
            json={"lent_to_name": "Alice", "lent_to_user_id": str(status_id)},
        )
        assert response.status_code == 422

        await _cleanup_status(status_id)

    async def test_lend_rejects_non_owned_status(
        self, client: AsyncClient, owner: User, book
    ):
        created = await client.post(
            "/api/v1/me/statuses/", json={"book_id": str(book.id), "status": "wishlist"}
        )
        status_id = created.json()["id"]

        response = await client.post(
            f"/api/v1/me/statuses/{status_id}/lend", json={"lent_to_name": "Alice"}
        )
        assert response.status_code == 409

        await _cleanup_status(status_id)

    async def test_return_rejects_non_lent_out_status(
        self, client: AsyncClient, owner: User, book
    ):
        created = await client.post(
            "/api/v1/me/statuses/", json={"book_id": str(book.id), "status": "owned"}
        )
        status_id = created.json()["id"]

        response = await client.post(f"/api/v1/me/statuses/{status_id}/return")
        assert response.status_code == 409

        await _cleanup_status(status_id)

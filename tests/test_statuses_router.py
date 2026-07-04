from collections.abc import AsyncIterator

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.main import app
from app.models.catalog import Book as BookModel
from app.models.user import User


def _login_as(user: User) -> None:
    app.dependency_overrides[get_current_user] = lambda: user


@pytest.fixture
async def owner(
    db_session: AsyncSession, async_client: AsyncClient
) -> AsyncIterator[User]:
    owner = User(email="owner@example.com", username="owner", display_name="Owner")
    db_session.add(owner)
    await db_session.commit()
    await db_session.refresh(owner)
    _login_as(owner)
    yield owner
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
async def other(db_session: AsyncSession) -> User:
    other = User(email="other@example.com", username="other", display_name="Other")
    db_session.add(other)
    await db_session.commit()
    await db_session.refresh(other)
    return other


@pytest.fixture
async def book(db_session: AsyncSession) -> BookModel:
    book = BookModel(title="Dune", description="Desert planet epic")
    db_session.add(book)
    await db_session.commit()
    await db_session.refresh(book)
    return book


class TestCreateStatus:
    async def test_requires_auth(self, async_client: AsyncClient, book: BookModel):
        response = await async_client.post(
            "/api/v1/me/statuses/", json={"book_id": str(book.id), "status": "owned"}
        )
        assert response.status_code == 401

    async def test_creates_status(
        self, async_client: AsyncClient, owner: User, book: BookModel
    ):
        response = await async_client.post(
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

    async def test_requires_exactly_one_target(
        self, async_client: AsyncClient, owner: User, book: BookModel
    ):
        response = await async_client.post(
            "/api/v1/me/statuses/", json={"status": "owned"}
        )
        assert response.status_code == 422


class TestListStatuses:
    async def test_filters_by_status_and_owner(
        self,
        async_client: AsyncClient,
        owner: User,
        other: User,
        book: BookModel,
    ):
        owned = await async_client.post(
            "/api/v1/me/statuses/", json={"book_id": str(book.id), "status": "owned"}
        )
        await async_client.post(
            "/api/v1/me/statuses/", json={"book_id": str(book.id), "status": "wishlist"}
        )

        response = await async_client.get(
            "/api/v1/me/statuses/", params={"status": "owned"}
        )
        assert response.status_code == 200
        data = response.json()
        assert {item["id"] for item in data} == {owned.json()["id"]}

        _login_as(other)
        other_response = await async_client.get("/api/v1/me/statuses/")
        assert other_response.json() == []

    async def test_requires_auth(self, async_client: AsyncClient):
        response = await async_client.get("/api/v1/me/statuses/")
        assert response.status_code == 401


class TestModifyStatus:
    async def test_updates_status(
        self, async_client: AsyncClient, owner: User, book: BookModel
    ):
        created = await async_client.post(
            "/api/v1/me/statuses/", json={"book_id": str(book.id), "status": "wishlist"}
        )
        status_id = created.json()["id"]

        response = await async_client.patch(
            f"/api/v1/me/statuses/{status_id}", json={"status": "owned"}
        )
        assert response.status_code == 200
        assert response.json()["status"] == "owned"

    async def test_not_found_for_non_owner(
        self,
        async_client: AsyncClient,
        owner: User,
        other: User,
        book: BookModel,
    ):
        created = await async_client.post(
            "/api/v1/me/statuses/", json={"book_id": str(book.id), "status": "owned"}
        )
        status_id = created.json()["id"]

        _login_as(other)
        response = await async_client.patch(
            f"/api/v1/me/statuses/{status_id}", json={"status": "sold"}
        )
        assert response.status_code == 404

    async def test_requires_auth(self, async_client: AsyncClient):
        response = await async_client.patch(
            "/api/v1/me/statuses/00000000-0000-0000-0000-000000000000",
            json={"status": "sold"},
        )
        assert response.status_code == 401


class TestDeleteStatus:
    async def test_deletes_status(
        self, async_client: AsyncClient, owner: User, book: BookModel
    ):
        created = await async_client.post(
            "/api/v1/me/statuses/", json={"book_id": str(book.id), "status": "owned"}
        )
        status_id = created.json()["id"]

        response = await async_client.delete(f"/api/v1/me/statuses/{status_id}")
        assert response.status_code == 204

        follow_up = await async_client.patch(
            f"/api/v1/me/statuses/{status_id}", json={"status": "sold"}
        )
        assert follow_up.status_code == 404

    async def test_not_found(self, async_client: AsyncClient, owner: User):
        response = await async_client.delete(
            "/api/v1/me/statuses/00000000-0000-0000-0000-000000000000"
        )
        assert response.status_code == 404

    async def test_requires_auth(self, async_client: AsyncClient):
        response = await async_client.delete(
            "/api/v1/me/statuses/00000000-0000-0000-0000-000000000000"
        )
        assert response.status_code == 401


class TestLendAndReturn:
    async def test_lend_marks_lent_out(
        self, async_client: AsyncClient, owner: User, book: BookModel
    ):
        created = await async_client.post(
            "/api/v1/me/statuses/", json={"book_id": str(book.id), "status": "owned"}
        )
        status_id = created.json()["id"]

        response = await async_client.post(
            f"/api/v1/me/statuses/{status_id}/lend",
            json={"lent_to_name": "Alice"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "lent_out"
        assert data["lent_to_name"] == "Alice"
        assert data["lent_at"] is not None
        assert data["returned_at"] is None

    async def test_return_reverts_to_owned(
        self, async_client: AsyncClient, owner: User, book: BookModel
    ):
        created = await async_client.post(
            "/api/v1/me/statuses/", json={"book_id": str(book.id), "status": "owned"}
        )
        status_id = created.json()["id"]
        await async_client.post(
            f"/api/v1/me/statuses/{status_id}/lend", json={"lent_to_name": "Alice"}
        )

        response = await async_client.post(f"/api/v1/me/statuses/{status_id}/return")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "owned"
        assert data["returned_at"] is not None
        assert data["lent_to_name"] is None
        assert data["lent_to_user_id"] is None

    async def test_lend_requires_exactly_one_target(
        self, async_client: AsyncClient, owner: User, book: BookModel
    ):
        created = await async_client.post(
            "/api/v1/me/statuses/", json={"book_id": str(book.id), "status": "owned"}
        )
        status_id = created.json()["id"]

        response = await async_client.post(
            f"/api/v1/me/statuses/{status_id}/lend",
            json={"lent_to_name": "Alice", "lent_to_user_id": str(status_id)},
        )
        assert response.status_code == 422

    async def test_lend_rejects_non_owned_status(
        self, async_client: AsyncClient, owner: User, book: BookModel
    ):
        created = await async_client.post(
            "/api/v1/me/statuses/", json={"book_id": str(book.id), "status": "wishlist"}
        )
        status_id = created.json()["id"]

        response = await async_client.post(
            f"/api/v1/me/statuses/{status_id}/lend", json={"lent_to_name": "Alice"}
        )
        assert response.status_code == 409

    async def test_return_rejects_non_lent_out_status(
        self, async_client: AsyncClient, owner: User, book: BookModel
    ):
        created = await async_client.post(
            "/api/v1/me/statuses/", json={"book_id": str(book.id), "status": "owned"}
        )
        status_id = created.json()["id"]

        response = await async_client.post(f"/api/v1/me/statuses/{status_id}/return")
        assert response.status_code == 409

    async def test_lend_requires_auth(self, async_client: AsyncClient):
        response = await async_client.post(
            "/api/v1/me/statuses/00000000-0000-0000-0000-000000000000/lend",
            json={"lent_to_name": "Alice"},
        )
        assert response.status_code == 401

    async def test_return_requires_auth(self, async_client: AsyncClient):
        response = await async_client.post(
            "/api/v1/me/statuses/00000000-0000-0000-0000-000000000000/return"
        )
        assert response.status_code == 401

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
async def book_alpha(db_session: AsyncSession) -> BookModel:
    book = BookModel(title="Alpha", description="First book")
    db_session.add(book)
    await db_session.commit()
    await db_session.refresh(book)
    return book


@pytest.fixture
async def book_zebra(db_session: AsyncSession) -> BookModel:
    book = BookModel(title="Zebra", description="Last book")
    db_session.add(book)
    await db_session.commit()
    await db_session.refresh(book)
    return book


VIEW_ENDPOINTS = [
    ("/api/v1/me/library", "owned"),
    ("/api/v1/me/wishlist", "wishlist"),
    ("/api/v1/me/lent-out", "lent_out"),
    ("/api/v1/me/borrowed", "borrowed"),
]


class TestAggregatedStatusViews:
    @pytest.mark.parametrize("path,kind", VIEW_ENDPOINTS)
    async def test_returns_only_matching_kind_for_owner(
        self,
        async_client: AsyncClient,
        owner: User,
        other: User,
        book_alpha: BookModel,
        book_zebra: BookModel,
        path: str,
        kind: str,
    ):
        matching = await async_client.post(
            "/api/v1/me/statuses/",
            json={"book_id": str(book_alpha.id), "status": kind},
        )
        await async_client.post(
            "/api/v1/me/statuses/",
            json={"book_id": str(book_zebra.id), "status": "sold"},
        )

        response = await async_client.get(path)
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["limit"] == 10
        assert data["offset"] == 0
        assert [item["id"] for item in data["items"]] == [matching.json()["id"]]
        assert data["items"][0]["status"] == kind

        _login_as(other)
        other_response = await async_client.get(path)
        assert other_response.json()["items"] == []
        assert other_response.json()["total"] == 0

    @pytest.mark.parametrize("path,kind", VIEW_ENDPOINTS)
    async def test_requires_auth(self, async_client: AsyncClient, path: str, kind: str):
        response = await async_client.get(path)
        assert response.status_code == 401

    @pytest.mark.parametrize("path,kind", VIEW_ENDPOINTS)
    async def test_pagination(
        self,
        async_client: AsyncClient,
        owner: User,
        book_alpha: BookModel,
        book_zebra: BookModel,
        path: str,
        kind: str,
    ):
        await async_client.post(
            "/api/v1/me/statuses/",
            json={"book_id": str(book_alpha.id), "status": kind},
        )
        await async_client.post(
            "/api/v1/me/statuses/",
            json={"book_id": str(book_zebra.id), "status": kind},
        )

        response = await async_client.get(path, params={"skip": 1, "limit": 1})
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert data["limit"] == 1
        assert data["offset"] == 1
        assert len(data["items"]) == 1

    @pytest.mark.parametrize("path,kind", VIEW_ENDPOINTS)
    async def test_rejects_limit_above_cap(
        self, async_client: AsyncClient, owner: User, path: str, kind: str
    ):
        response = await async_client.get(path, params={"limit": 101})
        assert response.status_code == 422

    @pytest.mark.parametrize("path,kind", VIEW_ENDPOINTS)
    async def test_sort_by_title(
        self,
        async_client: AsyncClient,
        owner: User,
        book_alpha: BookModel,
        book_zebra: BookModel,
        path: str,
        kind: str,
    ):
        await async_client.post(
            "/api/v1/me/statuses/",
            json={"book_id": str(book_zebra.id), "status": kind},
        )
        await async_client.post(
            "/api/v1/me/statuses/",
            json={"book_id": str(book_alpha.id), "status": kind},
        )

        response = await async_client.get(path, params={"sort": "title"})
        assert response.status_code == 200
        data = response.json()
        assert [item["book_id"] for item in data["items"]] == [
            str(book_alpha.id),
            str(book_zebra.id),
        ]

    @pytest.mark.parametrize("path,kind", VIEW_ENDPOINTS)
    async def test_sort_by_acquired_at_defaults_most_recent_first(
        self,
        async_client: AsyncClient,
        owner: User,
        book_alpha: BookModel,
        book_zebra: BookModel,
        path: str,
        kind: str,
    ):
        first = await async_client.post(
            "/api/v1/me/statuses/",
            json={"book_id": str(book_alpha.id), "status": kind},
        )
        second = await async_client.post(
            "/api/v1/me/statuses/",
            json={"book_id": str(book_zebra.id), "status": kind},
        )

        response = await async_client.get(path)
        assert response.status_code == 200
        data = response.json()
        assert [item["id"] for item in data["items"]] == [
            second.json()["id"],
            first.json()["id"],
        ]

    async def test_lent_out_includes_borrower_info(
        self, async_client: AsyncClient, owner: User, book_alpha: BookModel
    ):
        created = await async_client.post(
            "/api/v1/me/statuses/",
            json={"book_id": str(book_alpha.id), "status": "owned"},
        )
        status_id = created.json()["id"]
        await async_client.post(
            f"/api/v1/me/statuses/{status_id}/lend",
            json={"lent_to_name": "Alice"},
        )

        response = await async_client.get("/api/v1/me/lent-out")
        assert response.status_code == 200
        data = response.json()["items"]
        assert len(data) == 1
        assert data[0]["lent_to_name"] == "Alice"
        assert data[0]["lent_to_user_id"] is None
        assert data[0]["lent_at"] is not None

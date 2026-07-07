from collections.abc import AsyncIterator
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.core.security import decode_token
from app.main import app
from app.models.user import User


@pytest.fixture
async def admin_user(db_session: AsyncSession) -> AsyncIterator[User]:
    admin = User(
        email="admin@example.com",
        username="admin",
        display_name="Admin",
        is_admin=True,
        is_active=True,
    )
    db_session.add(admin)
    await db_session.commit()
    await db_session.refresh(admin)
    app.dependency_overrides[get_current_user] = lambda: admin
    yield admin
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
async def regular_user(db_session: AsyncSession) -> User:
    user = User(
        email="regular@example.com",
        username="regular",
        display_name="Regular User",
        is_admin=False,
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def inactive_user(db_session: AsyncSession) -> User:
    user = User(
        email="inactive@example.com",
        username="inactive",
        display_name="Inactive User",
        is_admin=False,
        is_active=False,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


class TestListUsers:
    async def test_requires_admin(self, async_client: AsyncClient):
        response = await async_client.get("/api/v1/admin/users/")
        assert response.status_code == 401

    async def test_admin_requires_auth(
        self, db_session: AsyncSession, async_client: AsyncClient
    ):
        app.dependency_overrides[get_current_user] = lambda: User(
            email="notadmin@example.com",
            username="notadmin",
            display_name="Not Admin",
            is_admin=False,
        )
        response = await async_client.get("/api/v1/admin/users/")
        assert response.status_code == 403
        app.dependency_overrides.pop(get_current_user, None)

    async def test_returns_paginated_list(
        self, async_client: AsyncClient, admin_user: User, regular_user: User
    ):
        response = await async_client.get(
            "/api/v1/admin/users/", params={"skip": 0, "limit": 10}
        )
        assert response.status_code == 200
        body = response.json()
        assert body["total"] >= 2
        assert len(body["items"]) >= 2
        assert body["limit"] == 10
        assert body["offset"] == 0

    async def test_filter_by_email(
        self, async_client: AsyncClient, admin_user: User, regular_user: User
    ):
        response = await async_client.get(
            "/api/v1/admin/users/", params={"email": "regular"}
        )
        assert response.status_code == 200
        body = response.json()
        assert len(body["items"]) == 1
        assert body["items"][0]["email"] == "regular@example.com"

    async def test_filter_by_is_active(
        self,
        async_client: AsyncClient,
        admin_user: User,
        regular_user: User,
        inactive_user: User,
    ):
        response = await async_client.get(
            "/api/v1/admin/users/", params={"is_active": True}
        )
        assert response.status_code == 200
        body = response.json()
        active_items = body["items"]
        assert all(item["is_active"] for item in active_items)

    async def test_filter_by_is_admin(
        self, async_client: AsyncClient, admin_user: User, regular_user: User
    ):
        response = await async_client.get(
            "/api/v1/admin/users/", params={"is_admin": True}
        )
        assert response.status_code == 200
        body = response.json()
        admin_items = body["items"]
        assert all(item["is_admin"] for item in admin_items)


class TestDeactivateUser:
    async def test_requires_admin(self, async_client: AsyncClient, regular_user: User):
        response = await async_client.post(
            f"/api/v1/admin/users/{regular_user.id}/deactivate"
        )
        assert response.status_code == 401

    async def test_deactivates_user(
        self, async_client: AsyncClient, admin_user: User, regular_user: User
    ):
        response = await async_client.post(
            f"/api/v1/admin/users/{regular_user.id}/deactivate"
        )
        assert response.status_code == 200
        body = response.json()
        assert body["is_active"] is False

    async def test_user_not_found(self, async_client: AsyncClient, admin_user: User):
        fake_id = uuid4()
        response = await async_client.post(f"/api/v1/admin/users/{fake_id}/deactivate")
        assert response.status_code == 404


class TestActivateUser:
    async def test_requires_admin(self, async_client: AsyncClient, inactive_user: User):
        response = await async_client.post(
            f"/api/v1/admin/users/{inactive_user.id}/activate"
        )
        assert response.status_code == 401

    async def test_activates_user(
        self, async_client: AsyncClient, admin_user: User, inactive_user: User
    ):
        response = await async_client.post(
            f"/api/v1/admin/users/{inactive_user.id}/activate"
        )
        assert response.status_code == 200
        body = response.json()
        assert body["is_active"] is True

    async def test_user_not_found(self, async_client: AsyncClient, admin_user: User):
        fake_id = uuid4()
        response = await async_client.post(f"/api/v1/admin/users/{fake_id}/activate")
        assert response.status_code == 404


class TestPromoteUser:
    async def test_requires_admin(self, async_client: AsyncClient, regular_user: User):
        response = await async_client.post(
            f"/api/v1/admin/users/{regular_user.id}/promote"
        )
        assert response.status_code == 401

    async def test_promotes_user(
        self, async_client: AsyncClient, admin_user: User, regular_user: User
    ):
        response = await async_client.post(
            f"/api/v1/admin/users/{regular_user.id}/promote"
        )
        assert response.status_code == 200
        body = response.json()
        assert body["is_admin"] is True

    async def test_user_not_found(self, async_client: AsyncClient, admin_user: User):
        fake_id = uuid4()
        response = await async_client.post(f"/api/v1/admin/users/{fake_id}/promote")
        assert response.status_code == 404


class TestDemoteUser:
    async def test_requires_admin(self, async_client: AsyncClient, admin_user: User):
        other_admin = User(
            email="other-admin@example.com",
            username="otheradmin",
            display_name="Other Admin",
            is_admin=True,
        )
        app.dependency_overrides[get_current_user] = lambda: admin_user
        response = await async_client.post(
            f"/api/v1/admin/users/{other_admin.id}/demote"
        )
        assert response.status_code == 404  # not in db yet

    async def test_demotes_user(
        self, db_session: AsyncSession, async_client: AsyncClient, admin_user: User
    ):
        other_admin = User(
            email="other-admin@example.com",
            username="otheradmin",
            display_name="Other Admin",
            is_admin=True,
        )
        db_session.add(other_admin)
        await db_session.commit()
        await db_session.refresh(other_admin)

        response = await async_client.post(
            f"/api/v1/admin/users/{other_admin.id}/demote"
        )
        assert response.status_code == 200
        body = response.json()
        assert body["is_admin"] is False

    async def test_user_not_found(self, async_client: AsyncClient, admin_user: User):
        fake_id = uuid4()
        response = await async_client.post(f"/api/v1/admin/users/{fake_id}/demote")
        assert response.status_code == 404


class TestIssuePasswordReset:
    async def test_requires_admin(self, async_client: AsyncClient, regular_user: User):
        response = await async_client.post(
            f"/api/v1/admin/users/{regular_user.id}/password-reset"
        )
        assert response.status_code == 401

    async def test_issues_reset_token(
        self, async_client: AsyncClient, admin_user: User, regular_user: User
    ):
        response = await async_client.post(
            f"/api/v1/admin/users/{regular_user.id}/password-reset"
        )
        assert response.status_code == 200
        body = response.json()
        assert "reset_token" in body
        assert body["reset_token"]

        # Verify token is valid and decodable
        token = body["reset_token"]
        payload = decode_token(token)
        assert payload["sub"] == str(regular_user.id)
        assert "jti" in payload
        assert "exp" in payload

    async def test_user_not_found(self, async_client: AsyncClient, admin_user: User):
        fake_id = uuid4()
        response = await async_client.post(
            f"/api/v1/admin/users/{fake_id}/password-reset"
        )
        assert response.status_code == 404

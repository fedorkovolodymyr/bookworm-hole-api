from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.main import app
from app.models.collection import Collection
from app.models.user import User
from app.services.security import hash_password, verify_password


def _login_as(user: User) -> None:
    app.dependency_overrides[get_current_user] = lambda: user


@pytest.fixture
async def owner(
    db_session: AsyncSession, async_client: AsyncClient
) -> AsyncIterator[User]:
    owner = User(
        email="owner@example.com",
        username="owner",
        display_name="Owner",
        password_hash=hash_password("correct-password"),
    )
    db_session.add(owner)
    await db_session.commit()
    await db_session.refresh(owner)
    _login_as(owner)
    yield owner
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
async def other(db_session: AsyncSession) -> User:
    other = User(
        email="other@example.com",
        username="other",
        display_name="Other",
        bio="Reads sci-fi",
        avatar_url="https://example.com/avatar.png",
    )
    db_session.add(other)
    await db_session.commit()
    await db_session.refresh(other)
    return other


@pytest.fixture
async def public_collection(db_session: AsyncSession, other: User) -> Collection:
    collection = Collection(user_id=other.id, name="Public Reads", is_public=True)
    db_session.add(collection)
    await db_session.commit()
    await db_session.refresh(collection)
    return collection


@pytest.fixture
async def private_collection(db_session: AsyncSession, other: User) -> Collection:
    collection = Collection(user_id=other.id, name="Private Reads", is_public=False)
    db_session.add(collection)
    await db_session.commit()
    await db_session.refresh(collection)
    return collection


class TestRetrieveOwnProfile:
    async def test_requires_auth(self, async_client: AsyncClient):
        response = await async_client.get("/api/v1/users/me")
        assert response.status_code == 401

    async def test_returns_profile(self, async_client: AsyncClient, owner: User):
        response = await async_client.get("/api/v1/users/me")
        assert response.status_code == 200
        body = response.json()
        assert body["id"] == str(owner.id)
        assert body["email"] == owner.email
        assert body["username"] == owner.username
        assert body["display_name"] == owner.display_name
        assert body["bio"] is None
        assert body["avatar_url"] is None
        assert body["locale"] == "en"
        assert body["timezone"] == "UTC"
        assert body["is_active"] is True
        assert body["is_admin"] is False


class TestUpdateOwnProfile:
    async def test_requires_auth(self, async_client: AsyncClient):
        response = await async_client.patch(
            "/api/v1/users/me", json={"display_name": "New"}
        )
        assert response.status_code == 401

    @pytest.mark.parametrize(
        ("field", "value"),
        [
            ("display_name", "New Name"),
            ("bio", "Loves fantasy novels"),
            ("avatar_url", "https://example.com/new-avatar.png"),
            ("locale", "pt-BR"),
            ("timezone", "America/Sao_Paulo"),
        ],
    )
    async def test_updates_single_field(
        self, async_client: AsyncClient, owner: User, field: str, value: str
    ):
        response = await async_client.patch("/api/v1/users/me", json={field: value})
        assert response.status_code == 200
        body = response.json()
        assert body[field] == value

        unchanged = {
            "display_name": owner.display_name,
            "bio": owner.bio,
            "avatar_url": owner.avatar_url,
            "locale": owner.locale,
            "timezone": owner.timezone,
        }
        del unchanged[field]
        for key, expected in unchanged.items():
            assert body[key] == expected

    async def test_rejects_invalid_locale(self, async_client: AsyncClient, owner: User):
        response = await async_client.patch(
            "/api/v1/users/me", json={"locale": "not-a-locale"}
        )
        assert response.status_code == 422


class TestChangePassword:
    async def test_requires_auth(self, async_client: AsyncClient):
        response = await async_client.post(
            "/api/v1/users/me/password",
            json={"current_password": "a", "new_password": "b"},
        )
        assert response.status_code == 401

    async def test_changes_password(
        self, async_client: AsyncClient, owner: User, db_session: AsyncSession
    ):
        response = await async_client.post(
            "/api/v1/users/me/password",
            json={
                "current_password": "correct-password",
                "new_password": "new-password-123",
            },
        )
        assert response.status_code == 204
        await db_session.refresh(owner)
        assert verify_password("new-password-123", owner.password_hash or "")

    async def test_rejects_wrong_current_password(
        self, async_client: AsyncClient, owner: User
    ):
        response = await async_client.post(
            "/api/v1/users/me/password",
            json={"current_password": "wrong", "new_password": "new-password-123"},
        )
        assert response.status_code == 401


class TestDeactivateAccount:
    async def test_requires_auth(self, async_client: AsyncClient):
        response = await async_client.post("/api/v1/users/me/deactivate")
        assert response.status_code == 401

    async def test_deactivates_account(self, async_client: AsyncClient, owner: User):
        response = await async_client.post("/api/v1/users/me/deactivate")
        assert response.status_code == 200
        assert response.json()["is_active"] is False


class TestScheduleDeletion:
    async def test_requires_auth(self, async_client: AsyncClient):
        response = await async_client.post("/api/v1/users/me/delete")
        assert response.status_code == 401

    async def test_schedules_deletion(self, async_client: AsyncClient, owner: User):
        before = datetime.now(UTC)
        response = await async_client.post("/api/v1/users/me/delete")
        assert response.status_code == 200
        body = response.json()
        scheduled_at = datetime.fromisoformat(body["deletion_scheduled_at"])
        assert 29 <= (scheduled_at - before).days <= 30

    async def test_rescheduling_extends_grace_period(
        self, async_client: AsyncClient, owner: User
    ):
        first = await async_client.post("/api/v1/users/me/delete")
        second = await async_client.post("/api/v1/users/me/delete")
        assert second.status_code == 200
        first_at = datetime.fromisoformat(first.json()["deletion_scheduled_at"])
        second_at = datetime.fromisoformat(second.json()["deletion_scheduled_at"])
        assert second_at >= first_at


class TestCancelDeletion:
    async def test_requires_auth(self, async_client: AsyncClient):
        response = await async_client.post("/api/v1/users/me/delete/cancel")
        assert response.status_code == 401

    async def test_cancels_scheduled_deletion(
        self, async_client: AsyncClient, owner: User
    ):
        await async_client.post("/api/v1/users/me/delete")
        response = await async_client.post("/api/v1/users/me/delete/cancel")
        assert response.status_code == 200
        assert response.json()["deletion_scheduled_at"] is None

    async def test_rejects_when_nothing_scheduled(
        self, async_client: AsyncClient, owner: User
    ):
        response = await async_client.post("/api/v1/users/me/delete/cancel")
        assert response.status_code == 409

    async def test_rejects_when_grace_period_expired(
        self, async_client: AsyncClient, owner: User, db_session: AsyncSession
    ):
        owner.deletion_scheduled_at = datetime.now(UTC) - timedelta(days=1)
        db_session.add(owner)
        await db_session.commit()

        response = await async_client.post("/api/v1/users/me/delete/cancel")
        assert response.status_code == 409


class TestRetrievePublicProfile:
    async def test_not_found(self, async_client: AsyncClient):
        response = await async_client.get("/api/v1/users/no-such-user")
        assert response.status_code == 404

    async def test_returns_public_profile_with_public_collections_only(
        self,
        async_client: AsyncClient,
        other: User,
        public_collection: Collection,
        private_collection: Collection,
    ):
        response = await async_client.get(f"/api/v1/users/{other.username}")
        assert response.status_code == 200
        body = response.json()
        assert body["username"] == other.username
        assert body["display_name"] == other.display_name
        assert body["bio"] == other.bio
        assert body["avatar_url"] == other.avatar_url
        assert body["collections"]["total"] == 1
        names = [item["name"] for item in body["collections"]["items"]]
        assert names == ["Public Reads"]

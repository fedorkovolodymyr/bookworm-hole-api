from collections.abc import AsyncIterator
from datetime import UTC, datetime

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.main import app
from app.models.catalog import Book as BookModel
from app.models.catalog import Release as ReleaseModel
from app.models.catalog import ReleaseFormat
from app.models.reading_session import ReadingSession
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
    book = BookModel(title="The Hobbit", description="A fantasy adventure")
    db_session.add(book)
    await db_session.commit()
    await db_session.refresh(book)
    return book


@pytest.fixture
async def release(db_session: AsyncSession, book: BookModel) -> ReleaseModel:
    release = ReleaseModel(
        book_id=book.id,
        format=ReleaseFormat.paperback,
        publisher="Allen & Unwin",
        language="en",
    )
    db_session.add(release)
    await db_session.commit()
    await db_session.refresh(release)
    return release


@pytest.fixture
async def other_release(db_session: AsyncSession, book: BookModel) -> ReleaseModel:
    release = ReleaseModel(
        book_id=book.id,
        format=ReleaseFormat.hardcover,
        publisher="Allen & Unwin",
        language="en",
    )
    db_session.add(release)
    await db_session.commit()
    await db_session.refresh(release)
    return release


@pytest.fixture
async def active_session(
    db_session: AsyncSession, owner: User, release: ReleaseModel
) -> ReadingSession:
    session = ReadingSession(
        user_id=owner.id,
        release_id=release.id,
        started_at=datetime.now(UTC),
        position_start=10,
    )
    db_session.add(session)
    await db_session.commit()
    await db_session.refresh(session)
    return session


class TestStartSession:
    async def test_requires_auth(
        self, async_client: AsyncClient, release: ReleaseModel
    ):
        app.dependency_overrides.pop(get_current_user, None)
        response = await async_client.post(
            "/api/v1/me/reading/start", json={"release_id": str(release.id)}
        )
        assert response.status_code == 401

    async def test_creates_active_session(
        self, async_client: AsyncClient, owner: User, release: ReleaseModel
    ):
        response = await async_client.post(
            "/api/v1/me/reading/start",
            json={"release_id": str(release.id), "position_start": 42},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["user_id"] == str(owner.id)
        assert data["release_id"] == str(release.id)
        assert data["position_start"] == 42
        assert data["ended_at"] is None

    async def test_rejects_duplicate_active_for_release(
        self,
        async_client: AsyncClient,
        owner: User,
        release: ReleaseModel,
        active_session: ReadingSession,
    ):
        response = await async_client.post(
            "/api/v1/me/reading/start", json={"release_id": str(release.id)}
        )
        assert response.status_code == 409

    async def test_allows_active_for_different_release(
        self,
        async_client: AsyncClient,
        owner: User,
        release: ReleaseModel,
        other_release: ReleaseModel,
        active_session: ReadingSession,
    ):
        response = await async_client.post(
            "/api/v1/me/reading/start", json={"release_id": str(other_release.id)}
        )
        assert response.status_code == 201
        assert response.json()["release_id"] == str(other_release.id)

    async def test_includes_optional_position_unit(
        self, async_client: AsyncClient, owner: User, release: ReleaseModel
    ):
        response = await async_client.post(
            "/api/v1/me/reading/start",
            json={
                "release_id": str(release.id),
                "position_start": 75,
                "position_unit": "percent",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["position_unit"] == "percent"


class TestStopSession:
    async def test_requires_auth(
        self,
        async_client: AsyncClient,
        release: ReleaseModel,
        active_session: ReadingSession,
    ):
        app.dependency_overrides.pop(get_current_user, None)
        response = await async_client.post(
            "/api/v1/me/reading/stop",
            json={"release_id": str(release.id)},
        )
        assert response.status_code == 401

    async def test_closes_active_session(
        self,
        async_client: AsyncClient,
        owner: User,
        release: ReleaseModel,
        active_session: ReadingSession,
    ):
        response = await async_client.post(
            "/api/v1/me/reading/stop",
            json={
                "release_id": str(release.id),
                "position_end": 150,
                "notes": "Halfway",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(active_session.id)
        assert data["ended_at"] is not None
        assert data["position_end"] == 150
        assert data["notes"] == "Halfway"

    async def test_returns_409_when_no_active_session(
        self, async_client: AsyncClient, owner: User, release: ReleaseModel
    ):
        response = await async_client.post(
            "/api/v1/me/reading/stop", json={"release_id": str(release.id)}
        )
        assert response.status_code == 409

    async def test_returns_409_for_wrong_release(
        self,
        async_client: AsyncClient,
        owner: User,
        release: ReleaseModel,
        other_release: ReleaseModel,
        active_session: ReadingSession,
    ):
        response = await async_client.post(
            "/api/v1/me/reading/stop", json={"release_id": str(other_release.id)}
        )
        assert response.status_code == 409

    async def test_stops_with_partial_data(
        self,
        async_client: AsyncClient,
        release: ReleaseModel,
        active_session: ReadingSession,
    ):
        response = await async_client.post(
            "/api/v1/me/reading/stop",
            json={"release_id": str(release.id), "position_end": 200},
        )
        assert response.status_code == 200
        assert response.json()["position_end"] == 200
        assert response.json()["notes"] is None


class TestListActiveSessions:
    async def test_requires_auth(self, async_client: AsyncClient):
        app.dependency_overrides.pop(get_current_user, None)
        response = await async_client.get("/api/v1/me/reading/active")
        assert response.status_code == 401

    async def test_lists_active_sessions(
        self, async_client: AsyncClient, owner: User, active_session: ReadingSession
    ):
        response = await async_client.get("/api/v1/me/reading/active")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["id"] == str(active_session.id)
        assert data[0]["ended_at"] is None

    async def test_empty_list_when_no_active(
        self, async_client: AsyncClient, owner: User
    ):
        response = await async_client.get("/api/v1/me/reading/active")
        assert response.status_code == 200
        assert response.json() == []

    async def test_filters_by_user(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        owner: User,
        other: User,
        release: ReleaseModel,
        active_session: ReadingSession,
    ):
        other_session = ReadingSession(
            user_id=other.id,
            release_id=release.id,
            started_at=datetime.now(UTC),
        )
        db_session.add(other_session)
        await db_session.commit()

        response = await async_client.get("/api/v1/me/reading/active")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["user_id"] == str(owner.id)


class TestListSessions:
    async def test_requires_auth(self, async_client: AsyncClient):
        app.dependency_overrides.pop(get_current_user, None)
        response = await async_client.get("/api/v1/me/reading/sessions")
        assert response.status_code == 401

    async def test_lists_all_sessions(
        self, async_client: AsyncClient, owner: User, active_session: ReadingSession
    ):
        response = await async_client.get("/api/v1/me/reading/sessions")
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        session_ids = [s["id"] for s in data]
        assert str(active_session.id) in session_ids

    async def test_filters_by_release(
        self,
        async_client: AsyncClient,
        owner: User,
        release: ReleaseModel,
        other_release: ReleaseModel,
        db_session: AsyncSession,
    ):
        session1 = ReadingSession(
            user_id=owner.id,
            release_id=release.id,
            started_at=datetime.now(UTC),
            ended_at=datetime.now(UTC),
        )
        session2 = ReadingSession(
            user_id=owner.id,
            release_id=other_release.id,
            started_at=datetime.now(UTC),
            ended_at=datetime.now(UTC),
        )
        db_session.add(session1)
        db_session.add(session2)
        await db_session.commit()

        response = await async_client.get(
            "/api/v1/me/reading/sessions", params={"release_id": str(release.id)}
        )
        assert response.status_code == 200
        data = response.json()
        assert all(s["release_id"] == str(release.id) for s in data)

    async def test_empty_list_when_no_sessions(
        self, async_client: AsyncClient, owner: User
    ):
        response = await async_client.get("/api/v1/me/reading/sessions")
        assert response.status_code == 200
        assert response.json() == []


class TestUpdateSession:
    @pytest.mark.parametrize(
        ("field", "value"),
        [
            ("position_start", 100),
            ("position_end", 200),
            ("position_unit", "page"),
            ("notes", "Updated notes"),
            ("pages_read", 50),
        ],
    )
    async def test_updates_each_field(
        self,
        async_client: AsyncClient,
        owner: User,
        active_session: ReadingSession,
        field: str,
        value: object,
    ):
        response = await async_client.patch(
            f"/api/v1/me/reading/sessions/{active_session.id}",
            json={field: value},
        )
        assert response.status_code == 200
        data = response.json()
        original = {
            "position_start": active_session.position_start,
            "position_end": active_session.position_end,
            "position_unit": active_session.position_unit,
            "notes": active_session.notes,
            "pages_read": active_session.pages_read,
        }
        for name, original_value in original.items():
            assert data[name] == (value if name == field else original_value)

    async def test_requires_auth(
        self, async_client: AsyncClient, active_session: ReadingSession
    ):
        app.dependency_overrides.pop(get_current_user, None)
        response = await async_client.patch(
            f"/api/v1/me/reading/sessions/{active_session.id}",
            json={"notes": "hijacked"},
        )
        assert response.status_code == 401

    async def test_not_found_for_non_owner(
        self,
        async_client: AsyncClient,
        owner: User,
        other: User,
        active_session: ReadingSession,
    ):
        _login_as(other)
        response = await async_client.patch(
            f"/api/v1/me/reading/sessions/{active_session.id}",
            json={"notes": "hijacked"},
        )
        assert response.status_code == 404

    async def test_not_found_for_missing_session(
        self, async_client: AsyncClient, owner: User
    ):
        response = await async_client.patch(
            "/api/v1/me/reading/sessions/00000000-0000-0000-0000-000000000000",
            json={"notes": "hijacked"},
        )
        assert response.status_code == 404


class TestDeleteSession:
    async def test_deletes_session(
        self, async_client: AsyncClient, owner: User, active_session: ReadingSession
    ):
        response = await async_client.delete(
            f"/api/v1/me/reading/sessions/{active_session.id}"
        )
        assert response.status_code == 204

        follow_up = await async_client.get("/api/v1/me/reading/sessions")
        assert response.status_code == 204
        sessions = follow_up.json()
        assert not any(s["id"] == str(active_session.id) for s in sessions)

    async def test_requires_auth(
        self, async_client: AsyncClient, active_session: ReadingSession
    ):
        app.dependency_overrides.pop(get_current_user, None)
        response = await async_client.delete(
            f"/api/v1/me/reading/sessions/{active_session.id}"
        )
        assert response.status_code == 401

    async def test_not_found_for_non_owner(
        self,
        async_client: AsyncClient,
        owner: User,
        other: User,
        active_session: ReadingSession,
    ):
        _login_as(other)
        response = await async_client.delete(
            f"/api/v1/me/reading/sessions/{active_session.id}"
        )
        assert response.status_code == 404

    async def test_not_found_for_missing_session(
        self, async_client: AsyncClient, owner: User
    ):
        response = await async_client.delete(
            "/api/v1/me/reading/sessions/00000000-0000-0000-0000-000000000000"
        )
        assert response.status_code == 404

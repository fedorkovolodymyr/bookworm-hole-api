import csv
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from io import StringIO

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.main import app
from app.models.book_status import BookStatus, BookStatusKind
from app.models.catalog import Book as BookModel
from app.models.catalog import (
    BookContributor,
    Contributor,
    ContributorRole,
    Release,
    ReleaseFormat,
)
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


@pytest.fixture
async def book_with_release(db_session: AsyncSession) -> BookModel:
    book = BookModel(title="Dune", description="Desert planet epic")
    db_session.add(book)
    await db_session.flush()

    release = Release(
        book_id=book.id,
        format=ReleaseFormat.hardcover,
        publisher="Ace Books",
        published_year=1965,
        language="en",
    )
    db_session.add(release)
    await db_session.flush()

    contributor = Contributor(
        full_name="Frank Herbert",
        sort_name="Herbert, Frank",
        slug="frank-herbert",
    )
    db_session.add(contributor)
    await db_session.flush()

    db_session.add(
        BookContributor(
            book_id=book.id,
            contributor_id=contributor.id,
            role=ContributorRole.author,
        )
    )
    await db_session.commit()
    await db_session.refresh(book, attribute_names=["releases", "contributors"])
    return book


class TestExportLibraryCSV:
    async def test_requires_auth(self, async_client: AsyncClient):
        response = await async_client.get("/api/v1/users/me/export/library.csv")
        assert response.status_code == 401

    async def test_empty_library(self, async_client: AsyncClient, owner: User):
        response = await async_client.get("/api/v1/users/me/export/library.csv")
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/csv; charset=utf-8"
        assert "attachment" in response.headers.get("content-disposition", "")

        reader = csv.reader(StringIO(response.text))
        rows = list(reader)
        assert len(rows) == 1
        assert rows[0] == [
            "book_title",
            "authors",
            "release_format",
            "publisher",
            "published_year",
            "language",
            "isbn",
            "status",
            "acquired_at",
            "notes",
        ]

    async def test_single_status_with_release(
        self,
        async_client: AsyncClient,
        owner: User,
        book_with_release: BookModel,
        db_session: AsyncSession,
    ):
        release = book_with_release.releases[0]
        status = BookStatus(
            user_id=owner.id,
            release_id=release.id,
            status=BookStatusKind.owned,
            acquired_at=datetime(2024, 1, 15, 12, 0, 0, tzinfo=UTC),
            notes="Great read",
        )
        db_session.add(status)
        await db_session.commit()

        response = await async_client.get("/api/v1/users/me/export/library.csv")
        assert response.status_code == 200

        reader = csv.reader(StringIO(response.text))
        rows = list(reader)
        assert len(rows) == 2
        assert rows[0][0] == "book_title"

        data_row = rows[1]
        assert data_row[0] == "Dune"
        assert data_row[1] == "Frank Herbert"
        assert data_row[2] == "hardcover"
        assert data_row[3] == "Ace Books"
        assert data_row[4] == "1965"
        assert data_row[5] == "en"
        assert data_row[7] == "owned"
        assert "2024-01-15" in data_row[8]
        assert data_row[9] == "Great read"

    async def test_multiple_statuses(
        self,
        async_client: AsyncClient,
        owner: User,
        book_with_release: BookModel,
        db_session: AsyncSession,
    ):
        release = book_with_release.releases[0]

        status1 = BookStatus(
            user_id=owner.id,
            release_id=release.id,
            status=BookStatusKind.owned,
            acquired_at=datetime(2024, 1, 15, tzinfo=UTC),
        )
        status2 = BookStatus(
            user_id=owner.id,
            book_id=book_with_release.id,
            status=BookStatusKind.wishlist,
            acquired_at=datetime(2024, 2, 1, tzinfo=UTC),
        )
        db_session.add(status1)
        db_session.add(status2)
        await db_session.commit()

        response = await async_client.get("/api/v1/users/me/export/library.csv")
        assert response.status_code == 200

        reader = csv.reader(StringIO(response.text))
        rows = list(reader)
        assert len(rows) == 3

        assert rows[1][0] == "Dune"
        assert rows[1][7] == "owned"

        assert rows[2][0] == "Dune"
        assert rows[2][7] == "wishlist"


class TestExportAccount:
    async def test_requires_auth(self, async_client: AsyncClient):
        response = await async_client.get("/api/v1/users/me/export/all.json")
        assert response.status_code == 401

    async def test_returns_empty_export_for_new_user(
        self, async_client: AsyncClient, owner: User
    ):
        response = await async_client.get("/api/v1/users/me/export/all.json")
        assert response.status_code == 200
        body = response.json()
        assert body["export_version"] == 1
        assert body["user"]["id"] == str(owner.id)
        assert body["user"]["email"] == owner.email
        assert body["user"]["username"] == owner.username
        assert body["user"]["display_name"] == owner.display_name
        assert body["collections"] == []
        assert body["statuses"] == []
        assert body["reviews"] == []
        assert body["reading_sessions"] == []
        assert body["friends"] == []

    async def test_returns_version_field(self, async_client: AsyncClient, owner: User):
        response = await async_client.get("/api/v1/users/me/export/all.json")
        assert response.status_code == 200
        body = response.json()
        assert "export_version" in body
        assert body["export_version"] == 1

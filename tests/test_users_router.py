import csv
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from io import StringIO

import pytest
from fastapi import Depends
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.deps import get_current_user
from app.core.encryption import encrypt
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
from app.models.google_integration import GoogleIntegration
from app.models.user import User
from app.repositories.backup_record_repository import BackupRecordRepository
from app.repositories.backup_restore_repository import BackupRestoreRepository
from app.repositories.book_status_repository import BookStatusRepository
from app.repositories.collection_repository import CollectionRepository
from app.repositories.google_integration_repository import GoogleIntegrationRepository
from app.repositories.reading_session_repository import ReadingSessionRepository
from app.repositories.review_repository import ReviewRepository
from app.routers.users import (
    get_backup_restore_service,
    get_backup_service,
    get_export_service,
)
from app.schemas.export_schemas import AccountExportResponse, ExportUserResponse
from app.services.backup_restore_service import BackupRestoreService
from app.services.backup_service import BackupService
from app.services.google_integration_service import GoogleIntegrationService
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

    async def test_rejects_limit_above_cap(
        self, async_client: AsyncClient, other: User
    ):
        response = await async_client.get(
            f"/api/v1/users/{other.username}", params={"limit": 101}
        )
        assert response.status_code == 422


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


class FakeDriveAdapter:
    def __init__(self) -> None:
        self.folder_calls: list[tuple[str, str]] = []
        self.uploads: list[tuple[str, str, str, bytes]] = []

    async def find_or_create_folder(self, access_token: str, folder_name: str) -> str:
        self.folder_calls.append((access_token, folder_name))
        return "fake-folder-id"

    async def upload_file(
        self, access_token: str, folder_id: str, filename: str, content: bytes
    ) -> str:
        self.uploads.append((access_token, folder_id, filename, content))
        return f"fake-file-{len(self.uploads)}"


@pytest.fixture
async def fake_drive_adapter() -> AsyncIterator[FakeDriveAdapter]:
    adapter = FakeDriveAdapter()

    def _get_backup_service(
        current_user: User = Depends(get_current_user),
        session: AsyncSession = Depends(get_session),
    ) -> BackupService:
        return BackupService(
            GoogleIntegrationService(GoogleIntegrationRepository(session)),
            get_export_service(current_user, session),
            BackupRecordRepository(session),
            adapter,
        )

    app.dependency_overrides[get_backup_service] = _get_backup_service
    yield adapter
    app.dependency_overrides.pop(get_backup_service, None)


@pytest.fixture
async def google_integration(
    db_session: AsyncSession, owner: User
) -> GoogleIntegration:
    integration = GoogleIntegration(
        user_id=owner.id,
        access_token_encrypted=encrypt("owner-access-token"),
        refresh_token_encrypted=encrypt("owner-refresh-token"),
        expires_at=datetime.now(UTC) + timedelta(hours=1),
        scopes=["https://www.googleapis.com/auth/drive.file"],
        connected_at=datetime.now(UTC),
    )
    db_session.add(integration)
    await db_session.commit()
    await db_session.refresh(integration)
    return integration


class TestCreateGoogleDriveBackup:
    async def test_requires_auth(self, async_client: AsyncClient):
        response = await async_client.post("/api/v1/users/me/backup/google-drive")
        assert response.status_code == 401

    async def test_no_integration_raises_not_found(
        self,
        async_client: AsyncClient,
        owner: User,
        fake_drive_adapter: FakeDriveAdapter,
    ):
        response = await async_client.post("/api/v1/users/me/backup/google-drive")
        assert response.status_code == 404

    async def test_creates_backup(
        self,
        async_client: AsyncClient,
        owner: User,
        google_integration: GoogleIntegration,
        fake_drive_adapter: FakeDriveAdapter,
    ):
        response = await async_client.post("/api/v1/users/me/backup/google-drive")

        assert response.status_code == 200
        body = response.json()
        assert body["drive_file_id"] == "fake-file-1"
        assert body["filename"].startswith("homelibrary-backup-")
        assert body["filename"].endswith(".json")
        assert "owner-access-token" not in response.text
        assert fake_drive_adapter.folder_calls == [
            ("owner-access-token", "HomeLibraryBackups")
        ]
        assert len(fake_drive_adapter.uploads) == 1


class TestGoogleDriveBackupHistory:
    async def test_requires_auth(self, async_client: AsyncClient):
        response = await async_client.get(
            "/api/v1/users/me/backup/google-drive/history"
        )
        assert response.status_code == 401

    async def test_empty_when_no_backups(self, async_client: AsyncClient, owner: User):
        response = await async_client.get(
            "/api/v1/users/me/backup/google-drive/history"
        )
        assert response.status_code == 200
        body = response.json()
        assert body["items"] == []
        assert body["total"] == 0

    async def test_rejects_limit_above_cap(
        self, async_client: AsyncClient, owner: User
    ):
        response = await async_client.get(
            "/api/v1/users/me/backup/google-drive/history", params={"limit": 101}
        )
        assert response.status_code == 422

    async def test_lists_backups_newest_first_paginated(
        self,
        async_client: AsyncClient,
        owner: User,
        google_integration: GoogleIntegration,
        fake_drive_adapter: FakeDriveAdapter,
    ):
        first = await async_client.post("/api/v1/users/me/backup/google-drive")
        second = await async_client.post("/api/v1/users/me/backup/google-drive")

        response = await async_client.get(
            "/api/v1/users/me/backup/google-drive/history", params={"limit": 1}
        )

        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 2
        assert body["limit"] == 1
        assert body["offset"] == 0
        assert len(body["items"]) == 1
        assert body["items"][0]["id"] == second.json()["id"]
        assert body["items"][0]["drive_file_id"] == second.json()["drive_file_id"]
        assert first.json()["id"] != second.json()["id"]


class FakeRestoreDriveAdapter:
    def __init__(self, content: bytes) -> None:
        self.content = content
        self.downloads: list[tuple[str, str]] = []

    async def download_file(self, access_token: str, file_id: str) -> bytes:
        self.downloads.append((access_token, file_id))
        return self.content


@pytest.fixture
async def fake_restore_drive_adapter(
    owner: User,
) -> AsyncIterator[FakeRestoreDriveAdapter]:
    export = AccountExportResponse(
        export_version=1,
        user=ExportUserResponse.model_validate(owner),
        collections=[],
        statuses=[],
        reviews=[],
        reading_sessions=[],
        friends=[],
    )
    adapter = FakeRestoreDriveAdapter(export.model_dump_json().encode("utf-8"))

    def _get_backup_restore_service(
        session: AsyncSession = Depends(get_session),
    ) -> BackupRestoreService:
        return BackupRestoreService(
            GoogleIntegrationService(GoogleIntegrationRepository(session)),
            BookStatusRepository(session),
            CollectionRepository(session),
            ReviewRepository(session),
            ReadingSessionRepository(session),
            BackupRestoreRepository(session),
            adapter,
        )

    app.dependency_overrides[get_backup_restore_service] = _get_backup_restore_service
    yield adapter
    app.dependency_overrides.pop(get_backup_restore_service, None)


class TestRestoreGoogleDriveBackup:
    async def test_requires_auth(self, async_client: AsyncClient):
        response = await async_client.post(
            "/api/v1/users/me/backup/google-drive/restore",
            json={"file_id": "file-id", "mode": "merge"},
        )
        assert response.status_code == 401

    async def test_no_integration_raises_not_found(
        self,
        async_client: AsyncClient,
        owner: User,
        fake_restore_drive_adapter: FakeRestoreDriveAdapter,
    ):
        response = await async_client.post(
            "/api/v1/users/me/backup/google-drive/restore",
            json={"file_id": "file-id", "mode": "merge"},
        )
        assert response.status_code == 404

    async def test_merge_restores_backup(
        self,
        async_client: AsyncClient,
        owner: User,
        google_integration: GoogleIntegration,
        fake_restore_drive_adapter: FakeRestoreDriveAdapter,
    ):
        response = await async_client.post(
            "/api/v1/users/me/backup/google-drive/restore",
            json={"file_id": "file-id", "mode": "merge"},
        )

        assert response.status_code == 200
        body = response.json()
        assert body["mode"] == "merge"
        assert body["collections"] == {"created": 0, "updated": 0, "skipped": 0}
        assert "owner-access-token" not in response.text
        assert fake_restore_drive_adapter.downloads == [
            ("owner-access-token", "file-id")
        ]

    async def test_replace_rejected_when_feature_flag_disabled(
        self,
        async_client: AsyncClient,
        owner: User,
        google_integration: GoogleIntegration,
        fake_restore_drive_adapter: FakeRestoreDriveAdapter,
    ):
        response = await async_client.post(
            "/api/v1/users/me/backup/google-drive/restore",
            json={"file_id": "file-id", "mode": "replace", "confirm": True},
        )
        assert response.status_code == 409

    async def test_replace_rejected_without_confirm(
        self,
        async_client: AsyncClient,
        owner: User,
        google_integration: GoogleIntegration,
        fake_restore_drive_adapter: FakeRestoreDriveAdapter,
        monkeypatch: pytest.MonkeyPatch,
    ):
        import app.core.config as config_module

        monkeypatch.setattr(
            config_module.settings.app_settings, "enable_backup_replace_mode", True
        )

        response = await async_client.post(
            "/api/v1/users/me/backup/google-drive/restore",
            json={"file_id": "file-id", "mode": "replace", "confirm": False},
        )
        assert response.status_code == 409

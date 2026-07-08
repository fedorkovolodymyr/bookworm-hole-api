from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

import app.core.config as config_module
from app.core.errors import ConflictError, ErrorMessages, NotFoundError
from app.models.book_status import BookStatus, BookStatusKind
from app.models.catalog import Book
from app.models.collection import Collection
from app.models.user import User
from app.repositories.backup_restore_repository import BackupRestoreRepository
from app.repositories.book_status_repository import BookStatusRepository
from app.repositories.collection_repository import CollectionRepository
from app.repositories.reading_session_repository import ReadingSessionRepository
from app.repositories.review_repository import ReviewRepository
from app.schemas.export_schemas import (
    AccountExportResponse,
    ExportBookStatusResponse,
    ExportCollectionResponse,
    ExportReviewResponse,
    ExportUserResponse,
)
from app.services.backup_restore_service import BackupRestoreService

_ACCESS_TOKEN = "super-secret-access-token"


class FakeIntegrationService:
    def __init__(self, token: str | None = _ACCESS_TOKEN) -> None:
        self.token = token
        self.requested_for: list[UUID] = []

    async def get_valid_access_token(self, user_id: UUID) -> str:
        self.requested_for.append(user_id)
        if self.token is None:
            raise NotFoundError(ErrorMessages.GOOGLE_INTEGRATION_NOT_FOUND)
        return self.token


class FakeDriveAdapter:
    def __init__(self, content: bytes) -> None:
        self.content = content
        self.downloads: list[tuple[str, str]] = []

    async def download_file(self, access_token: str, file_id: str) -> bytes:
        self.downloads.append((access_token, file_id))
        return self.content


def _export_payload(
    user: User,
    *,
    collections: list[ExportCollectionResponse] | None = None,
    statuses: list[ExportBookStatusResponse] | None = None,
    reviews: list[ExportReviewResponse] | None = None,
) -> bytes:
    export = AccountExportResponse(
        export_version=1,
        user=ExportUserResponse.model_validate(user),
        collections=collections or [],
        statuses=statuses or [],
        reviews=reviews or [],
        reading_sessions=[],
        friends=[],
    )
    return export.model_dump_json().encode("utf-8")


async def _make_user(
    db_session: AsyncSession, email: str = "reader@example.com"
) -> User:
    user = User(email=email, username=email.split("@")[0], display_name=email)
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


async def _make_book(db_session: AsyncSession) -> Book:
    book = Book(title="Dune", description="Desert planet epic")
    db_session.add(book)
    await db_session.commit()
    await db_session.refresh(book)
    return book


def _service(
    db_session: AsyncSession,
    integration_service: FakeIntegrationService,
    drive_adapter: FakeDriveAdapter,
) -> BackupRestoreService:
    return BackupRestoreService(
        integration_service,
        BookStatusRepository(db_session),
        CollectionRepository(db_session),
        ReviewRepository(db_session),
        ReadingSessionRepository(db_session),
        BackupRestoreRepository(db_session),
        drive_adapter,
    )


class TestRestoreNoIntegration:
    async def test_raises_not_found_when_not_connected(self, db_session: AsyncSession):
        user = await _make_user(db_session)
        integration_service = FakeIntegrationService(token=None)
        service = _service(
            db_session, integration_service, FakeDriveAdapter(_export_payload(user))
        )

        with pytest.raises(NotFoundError):
            await service.restore(user.id, "file-id", "merge", confirm=False)


class TestRestoreMerge:
    async def test_creates_collections_statuses_and_reviews(
        self, db_session: AsyncSession
    ):
        user = await _make_user(db_session)
        book = await _make_book(db_session)
        payload = _export_payload(
            user,
            collections=[
                ExportCollectionResponse(
                    id=uuid4(),
                    name="Favorites",
                    description="My favorite reads",
                    is_public=False,
                    cover_image_url=None,
                    sort_order=0,
                    created_at=datetime.now(UTC),
                    updated_at=datetime.now(UTC),
                )
            ],
            statuses=[
                ExportBookStatusResponse(
                    id=uuid4(),
                    book_id=book.id,
                    release_id=None,
                    status=BookStatusKind.owned,
                    acquired_at=None,
                    notes=None,
                    lent_to_user_id=None,
                    lent_to_name=None,
                    lent_at=None,
                    returned_at=None,
                    created_at=datetime.now(UTC),
                    updated_at=datetime.now(UTC),
                )
            ],
            reviews=[
                ExportReviewResponse(
                    id=uuid4(),
                    book_id=book.id,
                    release_id=None,
                    rating=5,
                    title="Loved it",
                    body="Great book",
                    is_public=True,
                    contains_spoilers=False,
                    created_at=datetime.now(UTC),
                    updated_at=datetime.now(UTC),
                )
            ],
        )
        service = _service(
            db_session, FakeIntegrationService(), FakeDriveAdapter(payload)
        )

        report = await service.restore(user.id, "file-id", "merge", confirm=False)

        assert report.mode == "merge"
        assert report.collections.created == 1
        assert report.book_statuses.created == 1
        assert report.reviews.created == 1

        collections = (
            (
                await db_session.execute(
                    select(Collection).where(Collection.user_id == user.id)
                )
            )
            .scalars()
            .all()
        )
        assert len(collections) == 1
        assert collections[0].name == "Favorites"

    async def test_rerunning_merge_does_not_duplicate(self, db_session: AsyncSession):
        user = await _make_user(db_session)
        book = await _make_book(db_session)
        payload = _export_payload(
            user,
            statuses=[
                ExportBookStatusResponse(
                    id=uuid4(),
                    book_id=book.id,
                    release_id=None,
                    status=BookStatusKind.owned,
                    acquired_at=None,
                    notes=None,
                    lent_to_user_id=None,
                    lent_to_name=None,
                    lent_at=None,
                    returned_at=None,
                    created_at=datetime.now(UTC),
                    updated_at=datetime.now(UTC),
                )
            ],
        )
        service = _service(
            db_session, FakeIntegrationService(), FakeDriveAdapter(payload)
        )

        first = await service.restore(user.id, "file-id", "merge", confirm=False)
        second = await service.restore(user.id, "file-id", "merge", confirm=False)

        assert first.book_statuses.created == 1
        assert second.book_statuses.created == 0
        assert second.book_statuses.skipped == 1

        statuses = (
            (
                await db_session.execute(
                    select(BookStatus).where(BookStatus.user_id == user.id)
                )
            )
            .scalars()
            .all()
        )
        assert len(statuses) == 1


class TestRestoreReplaceGating:
    async def test_rejected_when_feature_flag_disabled(
        self, db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
    ):
        monkeypatch.setattr(
            config_module.settings.app_settings, "enable_backup_replace_mode", False
        )
        user = await _make_user(db_session)
        service = _service(
            db_session,
            FakeIntegrationService(),
            FakeDriveAdapter(_export_payload(user)),
        )

        with pytest.raises(ConflictError) as exc_info:
            await service.restore(user.id, "file-id", "replace", confirm=True)
        assert exc_info.value.detail == ErrorMessages.BACKUP_REPLACE_MODE_DISABLED

    async def test_rejected_without_confirm(
        self, db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
    ):
        monkeypatch.setattr(
            config_module.settings.app_settings, "enable_backup_replace_mode", True
        )
        user = await _make_user(db_session)
        service = _service(
            db_session,
            FakeIntegrationService(),
            FakeDriveAdapter(_export_payload(user)),
        )

        with pytest.raises(ConflictError) as exc_info:
            await service.restore(user.id, "file-id", "replace", confirm=False)
        assert (
            exc_info.value.detail == ErrorMessages.BACKUP_REPLACE_CONFIRMATION_REQUIRED
        )


class TestRestoreReplace:
    async def test_wipes_existing_data_then_restores_backup(
        self, db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
    ):
        monkeypatch.setattr(
            config_module.settings.app_settings, "enable_backup_replace_mode", True
        )
        user = await _make_user(db_session)
        book = await _make_book(db_session)

        db_session.add(Collection(user_id=user.id, name="Stale Collection"))
        db_session.add(
            BookStatus(user_id=user.id, book_id=book.id, status=BookStatusKind.wishlist)
        )
        await db_session.commit()

        payload = _export_payload(
            user,
            collections=[
                ExportCollectionResponse(
                    id=uuid4(),
                    name="Fresh Collection",
                    description=None,
                    is_public=False,
                    cover_image_url=None,
                    sort_order=0,
                    created_at=datetime.now(UTC),
                    updated_at=datetime.now(UTC),
                )
            ],
            statuses=[
                ExportBookStatusResponse(
                    id=uuid4(),
                    book_id=book.id,
                    release_id=None,
                    status=BookStatusKind.owned,
                    acquired_at=None,
                    notes=None,
                    lent_to_user_id=None,
                    lent_to_name=None,
                    lent_at=None,
                    returned_at=None,
                    created_at=datetime.now(UTC),
                    updated_at=datetime.now(UTC),
                )
            ],
        )
        service = _service(
            db_session, FakeIntegrationService(), FakeDriveAdapter(payload)
        )

        report = await service.restore(user.id, "file-id", "replace", confirm=True)

        assert report.mode == "replace"
        assert report.collections.created == 1
        assert report.book_statuses.created == 1

        collections = (
            (
                await db_session.execute(
                    select(Collection).where(Collection.user_id == user.id)
                )
            )
            .scalars()
            .all()
        )
        assert [c.name for c in collections] == ["Fresh Collection"]

        statuses = (
            (
                await db_session.execute(
                    select(BookStatus).where(BookStatus.user_id == user.id)
                )
            )
            .scalars()
            .all()
        )
        assert len(statuses) == 1
        assert statuses[0].status == BookStatusKind.owned

    async def test_leaves_other_users_data_untouched(
        self, db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
    ):
        monkeypatch.setattr(
            config_module.settings.app_settings, "enable_backup_replace_mode", True
        )
        user = await _make_user(db_session, email="restoring@example.com")
        other = await _make_user(db_session, email="other@example.com")
        db_session.add(Collection(user_id=other.id, name="Keep Me"))
        await db_session.commit()

        service = _service(
            db_session,
            FakeIntegrationService(),
            FakeDriveAdapter(_export_payload(user)),
        )

        await service.restore(user.id, "file-id", "replace", confirm=True)

        other_collections = (
            (
                await db_session.execute(
                    select(Collection).where(Collection.user_id == other.id)
                )
            )
            .scalars()
            .all()
        )
        assert [c.name for c in other_collections] == ["Keep Me"]


class TestRestoreDoesNotLeakToken:
    async def test_report_and_drive_call_never_contain_raw_token(
        self, db_session: AsyncSession
    ):
        user = await _make_user(db_session)
        drive_adapter = FakeDriveAdapter(_export_payload(user))
        integration_service = FakeIntegrationService()
        service = _service(db_session, integration_service, drive_adapter)

        report = await service.restore(user.id, "file-id", "merge", confirm=False)

        assert drive_adapter.downloads == [(_ACCESS_TOKEN, "file-id")]
        assert _ACCESS_TOKEN not in report.model_dump_json()

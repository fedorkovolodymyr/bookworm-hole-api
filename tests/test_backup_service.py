from uuid import UUID, uuid4

import pytest

from app.core.errors import ErrorMessages, NotFoundError
from app.models.backup_record import BackupRecord
from app.schemas.export_schemas import AccountExportResponse, ExportUserResponse
from app.services.backup_service import BackupService

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


class FakeExportService:
    def __init__(self) -> None:
        self.export_calls = 0

    async def export_account(self) -> AccountExportResponse:
        self.export_calls += 1
        return AccountExportResponse(
            export_version=1,
            user=ExportUserResponse(
                id=uuid4(),
                email="reader@example.com",
                username="reader",
                display_name="Reader",
                bio=None,
                avatar_url=None,
                locale="en",
                timezone="UTC",
                is_active=True,
                is_admin=False,
            ),
            collections=[],
            statuses=[],
            reviews=[],
            reading_sessions=[],
            friends=[],
        )


class FakeDriveAdapter:
    def __init__(self) -> None:
        self.folder_calls: list[tuple[str, str]] = []
        self.uploads: list[tuple[str, str, str, bytes]] = []
        self.folder_id = "folder-id"
        self.file_id = "file-id"

    async def find_or_create_folder(self, access_token: str, folder_name: str) -> str:
        self.folder_calls.append((access_token, folder_name))
        return self.folder_id

    async def upload_file(
        self, access_token: str, folder_id: str, filename: str, content: bytes
    ) -> str:
        self.uploads.append((access_token, folder_id, filename, content))
        return self.file_id


class FakeBackupRepository:
    def __init__(self) -> None:
        self.records: list[BackupRecord] = []

    async def create(
        self, user_id: UUID, drive_file_id: str, filename: str
    ) -> BackupRecord:
        record = BackupRecord(
            user_id=user_id, drive_file_id=drive_file_id, filename=filename
        )
        self.records.append(record)
        return record

    async def get_all_for_user(
        self, user_id: UUID, skip: int = 0, limit: int = 10
    ) -> tuple[list[BackupRecord], int]:
        items = sorted(
            (r for r in self.records if r.user_id == user_id),
            key=lambda r: r.created_at,
            reverse=True,
        )
        return items[skip : skip + limit], len(items)


@pytest.fixture
def integration_service() -> FakeIntegrationService:
    return FakeIntegrationService()


@pytest.fixture
def export_service() -> FakeExportService:
    return FakeExportService()


@pytest.fixture
def drive_adapter() -> FakeDriveAdapter:
    return FakeDriveAdapter()


@pytest.fixture
def repository() -> FakeBackupRepository:
    return FakeBackupRepository()


@pytest.fixture
def service(
    integration_service: FakeIntegrationService,
    export_service: FakeExportService,
    drive_adapter: FakeDriveAdapter,
    repository: FakeBackupRepository,
) -> BackupService:
    return BackupService(integration_service, export_service, repository, drive_adapter)


class TestCreateBackup:
    async def test_no_integration_raises_not_found(
        self, integration_service: FakeIntegrationService, service: BackupService
    ):
        integration_service.token = None

        with pytest.raises(NotFoundError):
            await service.create_backup(uuid4())

    async def test_creates_folder_uploads_and_records(
        self,
        service: BackupService,
        drive_adapter: FakeDriveAdapter,
        export_service: FakeExportService,
        repository: FakeBackupRepository,
    ):
        user_id = uuid4()

        record = await service.create_backup(user_id)

        assert export_service.export_calls == 1
        assert drive_adapter.folder_calls == [(_ACCESS_TOKEN, "HomeLibraryBackups")]
        assert len(drive_adapter.uploads) == 1
        access_token, folder_id, filename, content = drive_adapter.uploads[0]
        assert access_token == _ACCESS_TOKEN
        assert folder_id == drive_adapter.folder_id
        assert filename.startswith("homelibrary-backup-")
        assert filename.endswith(".json")
        assert b"reader@example.com" in content

        assert record.user_id == user_id
        assert record.drive_file_id == drive_adapter.file_id
        assert record.filename == filename
        assert repository.records == [record]

    async def test_never_persists_access_token(
        self, service: BackupService, repository: FakeBackupRepository
    ):
        record = await service.create_backup(uuid4())

        assert _ACCESS_TOKEN not in record.drive_file_id
        assert _ACCESS_TOKEN not in record.filename
        assert not hasattr(record, "access_token")


class TestListHistory:
    async def test_empty_when_no_backups(self, service: BackupService):
        page = await service.list_history(uuid4())

        assert page.items == []
        assert page.total == 0

    async def test_returns_newest_first_and_paginates(
        self, service: BackupService, repository: FakeBackupRepository
    ):
        user_id = uuid4()
        first = await service.create_backup(user_id)
        second = await service.create_backup(user_id)

        page = await service.list_history(user_id, skip=0, limit=1)

        assert page.total == 2
        assert page.limit == 1
        assert page.offset == 0
        assert [item.id for item in page.items] in ([first.id], [second.id])

    async def test_scopes_to_requested_user(
        self, service: BackupService, repository: FakeBackupRepository
    ):
        await service.create_backup(uuid4())

        page = await service.list_history(uuid4())

        assert page.items == []
        assert page.total == 0

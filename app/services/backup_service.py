from datetime import UTC, datetime
from uuid import UUID

from app.models.backup_record import BackupRecord
from app.repositories.backup_record_repository import BackupRecordRepository
from app.schemas.common_schemas import Page
from app.services.external.google_drive import GoogleDriveAdapter
from app.services.google_integration_service import GoogleIntegrationService
from app.services.user_export_service import UserExportService

_BACKUP_FOLDER_NAME = "HomeLibraryBackups"


class BackupService:
    def __init__(
        self,
        integration_service: GoogleIntegrationService,
        export_service: UserExportService,
        repository: BackupRecordRepository,
        drive_adapter: GoogleDriveAdapter | None = None,
    ) -> None:
        self.integration_service = integration_service
        self.export_service = export_service
        self.repository = repository
        self.drive_adapter = drive_adapter or GoogleDriveAdapter()

    async def create_backup(self, user_id: UUID) -> BackupRecord:
        access_token = await self.integration_service.get_valid_access_token(user_id)
        export = await self.export_service.export_account()

        folder_id = await self.drive_adapter.find_or_create_folder(
            access_token, _BACKUP_FOLDER_NAME
        )
        timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        filename = f"homelibrary-backup-{timestamp}.json"
        content = export.model_dump_json().encode("utf-8")
        drive_file_id = await self.drive_adapter.upload_file(
            access_token, folder_id, filename, content
        )

        return await self.repository.create(user_id, drive_file_id, filename)

    async def list_history(
        self, user_id: UUID, skip: int = 0, limit: int = 10
    ) -> Page[BackupRecord]:
        items, total = await self.repository.get_all_for_user(user_id, skip, limit)
        return Page(items=list(items), total=total, limit=limit, offset=skip)

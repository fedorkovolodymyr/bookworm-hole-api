from typing import Literal
from uuid import UUID

from loguru import logger
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import settings
from app.core.errors import ConflictError, ErrorMessages
from app.models.book_status import BookStatus
from app.models.collection import Collection
from app.models.reading_session import ReadingSession
from app.models.review import Review
from app.repositories.backup_restore_repository import BackupRestoreRepository
from app.repositories.book_status_repository import BookStatusRepository
from app.repositories.collection_repository import CollectionRepository
from app.repositories.reading_session_repository import ReadingSessionRepository
from app.repositories.review_repository import ReviewRepository
from app.schemas.backup_schemas import BackupRestoreReport, RestoreCounts
from app.schemas.export_schemas import AccountExportResponse
from app.services.external.google_drive import GoogleDriveAdapter
from app.services.google_integration_service import GoogleIntegrationService

RestoreMode = Literal["merge", "replace"]

_EntityCounts = dict[str, RestoreCounts]


class BackupRestoreService:
    def __init__(
        self,
        integration_service: GoogleIntegrationService,
        book_status_repository: BookStatusRepository,
        collection_repository: CollectionRepository,
        review_repository: ReviewRepository,
        reading_session_repository: ReadingSessionRepository,
        restore_repository: BackupRestoreRepository,
        drive_adapter: GoogleDriveAdapter | None = None,
    ) -> None:
        self.integration_service = integration_service
        self.book_status_repository = book_status_repository
        self.collection_repository = collection_repository
        self.review_repository = review_repository
        self.reading_session_repository = reading_session_repository
        self.restore_repository = restore_repository
        self.drive_adapter = drive_adapter or GoogleDriveAdapter()

    async def restore(
        self, user_id: UUID, file_id: str, mode: RestoreMode, confirm: bool
    ) -> BackupRestoreReport:
        logger.info(
            f"Backup restore initiated user_id={user_id} mode={mode} file_id={file_id}"
        )

        if mode == "replace":
            if not settings.app_settings.enable_backup_replace_mode:
                raise ConflictError(ErrorMessages.BACKUP_REPLACE_MODE_DISABLED)
            if not confirm:
                raise ConflictError(ErrorMessages.BACKUP_REPLACE_CONFIRMATION_REQUIRED)

        access_token = await self.integration_service.get_valid_access_token(user_id)
        content = await self.drive_adapter.download_file(access_token, file_id)
        export = AccountExportResponse.model_validate_json(content)

        try:
            counts = (
                await self._restore_replace(user_id, export)
                if mode == "replace"
                else await self._restore_merge(user_id, export)
            )
        except SQLAlchemyError:
            await self.restore_repository.rollback()
            logger.error(f"Backup restore failed user_id={user_id} mode={mode}")
            raise

        logger.info(
            f"Backup restore completed user_id={user_id} mode={mode} "
            f"collections={counts['collections']} "
            f"book_statuses={counts['book_statuses']} "
            f"reviews={counts['reviews']} "
            f"reading_sessions={counts['reading_sessions']}"
        )
        return BackupRestoreReport(mode=mode, **counts)

    async def _restore_merge(
        self, user_id: UUID, export: AccountExportResponse
    ) -> _EntityCounts:
        """Union with existing data: creates anything not already present,
        matched by a stable natural key per entity type. Existing rows are
        left untouched (not overwritten) so a re-run is idempotent and never
        produces duplicates."""
        collections = RestoreCounts()
        for item in export.collections:
            if await self.restore_repository.find_collection(user_id, item.name):
                collections.skipped += 1
                continue
            await self.collection_repository.create(
                Collection(
                    user_id=user_id,
                    name=item.name,
                    description=item.description,
                    is_public=item.is_public,
                    cover_image_url=item.cover_image_url,
                    sort_order=item.sort_order,
                )
            )
            collections.created += 1

        book_statuses = RestoreCounts()
        for status_item in export.statuses:
            existing = await self.restore_repository.find_book_status(
                user_id, status_item.book_id, status_item.release_id, status_item.status
            )
            if existing:
                book_statuses.skipped += 1
                continue
            await self.book_status_repository.create(
                BookStatus(
                    user_id=user_id,
                    book_id=status_item.book_id,
                    release_id=status_item.release_id,
                    status=status_item.status,
                    acquired_at=status_item.acquired_at,
                    notes=status_item.notes,
                    lent_to_user_id=status_item.lent_to_user_id,
                    lent_to_name=status_item.lent_to_name,
                    lent_at=status_item.lent_at,
                    returned_at=status_item.returned_at,
                )
            )
            book_statuses.created += 1

        reviews = RestoreCounts()
        for review_item in export.reviews:
            existing = await self.review_repository.get_by_user_and_target(
                user_id, review_item.book_id, review_item.release_id
            )
            if existing:
                reviews.skipped += 1
                continue
            await self.review_repository.create(
                Review(
                    user_id=user_id,
                    book_id=review_item.book_id,
                    release_id=review_item.release_id,
                    rating=review_item.rating,
                    title=review_item.title,
                    body=review_item.body,
                    is_public=review_item.is_public,
                    contains_spoilers=review_item.contains_spoilers,
                )
            )
            reviews.created += 1

        reading_sessions = RestoreCounts()
        for session_item in export.reading_sessions:
            existing = await self.restore_repository.find_reading_session(
                user_id, session_item.release_id, session_item.started_at
            )
            if existing:
                reading_sessions.skipped += 1
                continue
            await self.reading_session_repository.create(
                ReadingSession(
                    user_id=user_id,
                    release_id=session_item.release_id,
                    started_at=session_item.started_at,
                    ended_at=session_item.ended_at,
                    pages_read=session_item.pages_read,
                    position_start=session_item.position_start,
                    position_end=session_item.position_end,
                    position_unit=session_item.position_unit,
                    notes=session_item.notes,
                )
            )
            reading_sessions.created += 1

        return {
            "collections": collections,
            "book_statuses": book_statuses,
            "reviews": reviews,
            "reading_sessions": reading_sessions,
        }

    async def _restore_replace(
        self, user_id: UUID, export: AccountExportResponse
    ) -> _EntityCounts:
        """Wipes then rewrites the user's owned data in one transaction: the
        purge and every insert stay uncommitted until the single commit at
        the end, so a failure anywhere in this method rolls the whole thing
        back and the account is never left half-wiped."""
        await self.restore_repository.purge_owned_data(user_id)

        for item in export.collections:
            self.restore_repository.add(
                Collection(
                    user_id=user_id,
                    name=item.name,
                    description=item.description,
                    is_public=item.is_public,
                    cover_image_url=item.cover_image_url,
                    sort_order=item.sort_order,
                )
            )
        for status_item in export.statuses:
            self.restore_repository.add(
                BookStatus(
                    user_id=user_id,
                    book_id=status_item.book_id,
                    release_id=status_item.release_id,
                    status=status_item.status,
                    acquired_at=status_item.acquired_at,
                    notes=status_item.notes,
                    lent_to_user_id=status_item.lent_to_user_id,
                    lent_to_name=status_item.lent_to_name,
                    lent_at=status_item.lent_at,
                    returned_at=status_item.returned_at,
                )
            )
        for review_item in export.reviews:
            self.restore_repository.add(
                Review(
                    user_id=user_id,
                    book_id=review_item.book_id,
                    release_id=review_item.release_id,
                    rating=review_item.rating,
                    title=review_item.title,
                    body=review_item.body,
                    is_public=review_item.is_public,
                    contains_spoilers=review_item.contains_spoilers,
                )
            )
        for session_item in export.reading_sessions:
            self.restore_repository.add(
                ReadingSession(
                    user_id=user_id,
                    release_id=session_item.release_id,
                    started_at=session_item.started_at,
                    ended_at=session_item.ended_at,
                    pages_read=session_item.pages_read,
                    position_start=session_item.position_start,
                    position_end=session_item.position_end,
                    position_unit=session_item.position_unit,
                    notes=session_item.notes,
                )
            )

        await self.restore_repository.commit()

        return {
            "collections": RestoreCounts(created=len(export.collections)),
            "book_statuses": RestoreCounts(created=len(export.statuses)),
            "reviews": RestoreCounts(created=len(export.reviews)),
            "reading_sessions": RestoreCounts(created=len(export.reading_sessions)),
        }

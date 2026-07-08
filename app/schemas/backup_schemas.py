from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class BackupRecordResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    drive_file_id: str
    filename: str
    created_at: datetime


class RestoreBackupSchema(BaseModel):
    file_id: str = Field(description="Google Drive file ID of the backup to restore")
    mode: Literal["merge", "replace"]
    confirm: bool = Field(
        default=False,
        description="Must be true when mode='replace'; ignored for 'merge'",
    )


class RestoreCounts(BaseModel):
    created: int = 0
    updated: int = 0
    skipped: int = 0


class BackupRestoreReport(BaseModel):
    mode: Literal["merge", "replace"]
    collections: RestoreCounts
    book_statuses: RestoreCounts
    reviews: RestoreCounts
    reading_sessions: RestoreCounts

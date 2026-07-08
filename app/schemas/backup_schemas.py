from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class BackupRecordResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    drive_file_id: str
    filename: str
    created_at: datetime

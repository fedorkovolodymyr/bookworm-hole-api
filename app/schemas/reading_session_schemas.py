from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.reading_session import PositionUnit


class CreateReadingSessionSchema(BaseModel):
    release_id: UUID
    position_start: int | None = None
    position_unit: PositionUnit | None = None


class StopReadingSessionSchema(BaseModel):
    release_id: UUID
    position_end: int | None = None
    notes: str | None = None


class UpdateReadingSessionSchema(BaseModel):
    started_at: datetime | None = None
    ended_at: datetime | None = None
    position_start: int | None = None
    position_end: int | None = None
    position_unit: PositionUnit | None = None
    pages_read: int | None = None
    notes: str | None = None


class ReadingSessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    release_id: UUID
    started_at: datetime
    ended_at: datetime | None
    position_start: int | None
    position_end: int | None
    position_unit: PositionUnit | None
    pages_read: int | None
    notes: str | None
    created_at: datetime
    updated_at: datetime

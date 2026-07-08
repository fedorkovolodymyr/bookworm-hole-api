from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.book_status import BookStatusKind
from app.models.reading_session import PositionUnit


class ExportUserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    username: str
    display_name: str
    bio: str | None
    avatar_url: str | None
    locale: str
    timezone: str
    is_active: bool
    is_admin: bool


class ExportCollectionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: str | None
    is_public: bool
    cover_image_url: str | None
    sort_order: int
    created_at: datetime
    updated_at: datetime


class ExportBookStatusResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    book_id: UUID | None
    release_id: UUID | None
    status: BookStatusKind
    acquired_at: datetime | None
    notes: str | None
    lent_to_user_id: UUID | None
    lent_to_name: str | None
    lent_at: datetime | None
    returned_at: datetime | None
    created_at: datetime
    updated_at: datetime


class ExportReviewResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    book_id: UUID | None
    release_id: UUID | None
    rating: int | None
    title: str | None
    body: str | None
    is_public: bool
    contains_spoilers: bool
    created_at: datetime
    updated_at: datetime


class ExportReadingSessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    release_id: UUID
    started_at: datetime
    ended_at: datetime | None
    pages_read: int | None
    position_start: int | None
    position_end: int | None
    position_unit: PositionUnit | None
    notes: str | None
    created_at: datetime
    updated_at: datetime


class ExportFriendResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: UUID
    username: str
    display_name: str
    avatar_url: str | None
    since: datetime


class AccountExportResponse(BaseModel):
    export_version: int
    user: ExportUserResponse
    collections: list[ExportCollectionResponse]
    statuses: list[ExportBookStatusResponse]
    reviews: list[ExportReviewResponse]
    reading_sessions: list[ExportReadingSessionResponse]
    friends: list[ExportFriendResponse]

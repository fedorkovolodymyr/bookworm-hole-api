from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, model_validator

from app.models.book_status import BookStatusKind


class CreateBookStatusSchema(BaseModel):
    book_id: UUID | None = None
    release_id: UUID | None = None
    status: BookStatusKind
    notes: str | None = None

    @model_validator(mode="after")
    def check_exactly_one_target(self) -> CreateBookStatusSchema:
        if (self.book_id is None) == (self.release_id is None):
            raise ValueError("exactly one of book_id or release_id is required")
        return self


class UpdateBookStatusSchema(BaseModel):
    status: BookStatusKind | None = None
    notes: str | None = None


class LendBookStatusSchema(BaseModel):
    lent_to_user_id: UUID | None = None
    lent_to_name: str | None = None

    @model_validator(mode="after")
    def check_exactly_one_target(self) -> LendBookStatusSchema:
        if (self.lent_to_user_id is None) == (self.lent_to_name is None):
            raise ValueError(
                "exactly one of lent_to_user_id or lent_to_name is required"
            )
        return self


class BookStatusResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
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

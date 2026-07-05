from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class CreateReviewSchema(BaseModel):
    book_id: UUID | None = None
    release_id: UUID | None = None
    rating: int | None = Field(default=None, ge=1, le=5)
    title: str | None = None
    body: str | None = None
    is_public: bool = True
    contains_spoilers: bool = False

    @model_validator(mode="after")
    def check_exactly_one_target(self) -> CreateReviewSchema:
        if (self.book_id is None) == (self.release_id is None):
            raise ValueError("exactly one of book_id or release_id is required")
        return self


class UpdateReviewSchema(BaseModel):
    rating: int | None = Field(default=None, ge=1, le=5)
    title: str | None = None
    body: str | None = None
    is_public: bool | None = None
    contains_spoilers: bool | None = None


class ReviewResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    book_id: UUID | None
    release_id: UUID | None
    rating: int | None
    title: str | None
    body: str | None
    is_public: bool
    contains_spoilers: bool
    created_at: datetime
    updated_at: datetime

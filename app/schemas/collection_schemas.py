from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, model_validator

from app.schemas.common_schemas import Page


class CreateCollectionSchema(BaseModel):
    name: str
    description: str | None = None
    is_public: bool = False
    cover_image_url: str | None = None


class UpdateCollectionSchema(BaseModel):
    name: str | None = None
    description: str | None = None
    is_public: bool | None = None
    cover_image_url: str | None = None


class CollectionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    name: str
    description: str | None
    is_public: bool
    cover_image_url: str | None
    sort_order: int
    created_at: datetime
    updated_at: datetime


class CollectionItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    collection_id: UUID
    book_id: UUID | None
    release_id: UUID | None
    position: int
    added_at: datetime
    note: str | None


class CollectionDetailResponse(CollectionResponse):
    items: Page[CollectionItemResponse]


class AddCollectionItemSchema(BaseModel):
    book_id: UUID | None = None
    release_id: UUID | None = None
    note: str | None = None

    @model_validator(mode="after")
    def check_exactly_one_target(self) -> AddCollectionItemSchema:
        if (self.book_id is None) == (self.release_id is None):
            raise ValueError("exactly one of book_id or release_id is required")
        return self


class UpdateCollectionItemSchema(BaseModel):
    position: int | None = None
    note: str | None = None


class ReorderItemsSchema(BaseModel):
    item_ids: list[UUID]

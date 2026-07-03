from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.catalog import ISBNKind, ReleaseFormat


class CreateBookSchema(BaseModel):
    title: str
    original_title: str | None = None
    original_language: str | None = None
    first_publication_year: int | None = None
    description: str


class UpdateBookSchema(BaseModel):
    title: str | None = None
    original_title: str | None = None
    original_language: str | None = None
    first_publication_year: int | None = None
    description: str | None = None


class BookResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    original_title: str | None
    original_language: str | None
    first_publication_year: int | None
    description: str
    created_at: datetime
    updated_at: datetime


class ISBNResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    code_normalized: str
    code_original: str
    kind: ISBNKind


class ReleaseWithISBNsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    format: ReleaseFormat
    publisher: str
    published_year: int | None
    language: str
    page_count: int | None
    duration_minutes: int | None
    cover_image_url: str | None
    description_override: str | None
    isbns: list[ISBNResponse]


class BookWithReleasesResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    original_title: str | None
    original_language: str | None
    first_publication_year: int | None
    description: str
    created_at: datetime
    updated_at: datetime
    releases: list[ReleaseWithISBNsResponse]

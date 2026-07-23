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
    genres: list[str]
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
    average_rating: float | None = None
    rating_count: int = 0


class BookWithReleasesResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    original_title: str | None
    original_language: str | None
    first_publication_year: int | None
    description: str
    genres: list[str]
    created_at: datetime
    updated_at: datetime
    releases: list[ReleaseWithISBNsResponse]
    average_rating: float | None = None
    rating_count: int = 0


class CreateReleaseSchema(BaseModel):
    book_id: UUID
    format: ReleaseFormat
    publisher: str
    published_year: int | None = None
    language: str
    page_count: int | None = None
    duration_minutes: int | None = None
    cover_image_url: str | None = None
    description_override: str | None = None


class ImportBookRequest(BaseModel):
    source: str
    source_id: str


class UpdateReleaseSchema(BaseModel):
    format: ReleaseFormat | None = None
    publisher: str | None = None
    published_year: int | None = None
    language: str | None = None
    page_count: int | None = None
    duration_minutes: int | None = None
    cover_image_url: str | None = None
    description_override: str | None = None

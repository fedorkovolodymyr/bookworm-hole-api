from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


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

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class CreateBookSchema(BaseModel):
    title: str
    description: str


class UpdateBookSchema(BaseModel):
    title: str | None = None
    description: str | None = None


class BookResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    description: str
    created_at: datetime
    updated_at: datetime

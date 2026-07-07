from uuid import UUID

from pydantic import BaseModel, Field


class BookshelfRowSchema(BaseModel):
    title: str
    author: str
    isbn: str | None = None
    status: str
    date_added: str | None = None


class ImportRowResultSchema(BaseModel):
    row_index: int
    status: str  # created, matched, skipped, failed
    reason: str | None = None
    book_id: UUID | None = None


class ImportReportSchema(BaseModel):
    created: int = Field(description="Rows resulting in new BookStatus")
    matched: int = Field(description="Rows matched to existing BookStatus")
    skipped: int = Field(description="Rows with no book resolution")
    failed: int = Field(description="Rows with errors")
    total: int = Field(description="Total rows processed")
    failures: list[ImportRowResultSchema] = Field(default_factory=lambda: [])

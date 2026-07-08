import enum
import uuid

from sqlalchemy import Column, Index, String
from sqlalchemy import Enum as SAEnum
from sqlmodel import Field, SQLModel

from app.models.mixins import IdMixin, TimestampMixin


class ImportRecordStatus(str, enum.Enum):
    pending = "pending"
    completed = "completed"
    failed = "failed"


class ImportRecord(SQLModel, IdMixin, TimestampMixin, table=True):
    __tablename__ = "import_records"
    __table_args__ = (
        Index("ix_import_records_user_id", "user_id"),
        Index("ix_import_records_user_id_file_hash", "user_id", "file_hash"),
        Index("ix_import_records_created_at", "created_at"),
    )

    user_id: uuid.UUID = Field(foreign_key="user.id", index=True)
    file_hash: str = Field(
        sa_column=Column(String(64), nullable=False),
        description="SHA256 hash of imported file for idempotency",
    )
    row_count: int = Field(default=0, description="Total rows in imported file")
    created_count: int = Field(
        default=0, description="Rows resulting in new BookStatus"
    )
    matched_count: int = Field(
        default=0, description="Rows matched to existing BookStatus"
    )
    skipped_count: int = Field(default=0, description="Rows with no book resolution")
    failed_count: int = Field(default=0, description="Rows with errors")
    status: ImportRecordStatus = Field(
        sa_column=Column(SAEnum(ImportRecordStatus), nullable=False),
        default=ImportRecordStatus.pending,
    )
    source_type: str = Field(
        max_length=64, description="Import source type (bookshelf, csv, goodreads)"
    )

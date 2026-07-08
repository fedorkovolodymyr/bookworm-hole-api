from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import Column, DateTime, ForeignKey, func
from sqlmodel import Field, SQLModel

from app.models.mixins import IdMixin


class BackupRecord(SQLModel, IdMixin, table=True):
    """History entry for a Google Drive backup upload."""

    user_id: UUID = Field(
        sa_column=Column(
            ForeignKey("user.id", ondelete="CASCADE"), nullable=False, index=True
        )
    )
    drive_file_id: str
    filename: str
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(
            DateTime(timezone=True),
            server_default=func.now(),
            nullable=False,
            index=True,
        ),
    )

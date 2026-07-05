import enum
import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, Index
from sqlalchemy import Enum as SAEnum
from sqlmodel import Field, SQLModel, text

from app.models.mixins import IdMixin, TimestampMixin


class PositionUnit(str, enum.Enum):
    page = "page"
    percent = "percent"
    location = "location"
    timestamp = "timestamp"


class ReadingSession(SQLModel, IdMixin, TimestampMixin, table=True):
    __tablename__ = "reading_sessions"
    __table_args__ = (
        Index(
            "uq_reading_session_active_user_release",
            "user_id",
            "release_id",
            unique=True,
            postgresql_where=text("ended_at IS NULL"),
        ),
    )

    user_id: uuid.UUID = Field(foreign_key="user.id", index=True)
    release_id: uuid.UUID = Field(foreign_key="releases.id", index=True)
    started_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False)
    )
    ended_at: datetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )
    pages_read: int | None = Field(default=None)
    position_start: int | None = Field(default=None)
    position_end: int | None = Field(default=None)
    position_unit: PositionUnit | None = Field(
        default=None, sa_column=Column(SAEnum(PositionUnit), nullable=True)
    )
    notes: str | None = Field(default=None)

import enum
import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, Column, DateTime, Index
from sqlalchemy import Enum as SAEnum
from sqlmodel import Field, SQLModel

from app.models.mixins import IdMixin, TimestampMixin


class BookStatusKind(str, enum.Enum):
    owned = "owned"
    wishlist = "wishlist"
    pre_order = "pre_order"
    lent_out = "lent_out"
    borrowed = "borrowed"
    gifted_away = "gifted_away"
    sold = "sold"
    lost = "lost"


class BookStatus(SQLModel, IdMixin, TimestampMixin, table=True):
    __tablename__ = "book_statuses"
    __table_args__ = (
        CheckConstraint(
            "(book_id IS NOT NULL AND release_id IS NULL) OR "
            "(book_id IS NULL AND release_id IS NOT NULL)",
            name="ck_book_status_exactly_one_target",
        ),
        Index("ix_book_statuses_user_id_status", "user_id", "status"),
    )

    user_id: uuid.UUID = Field(foreign_key="user.id", index=True)
    book_id: uuid.UUID | None = Field(default=None, foreign_key="book.id", index=True)
    release_id: uuid.UUID | None = Field(
        default=None, foreign_key="releases.id", index=True
    )
    status: BookStatusKind = Field(
        sa_column=Column(SAEnum(BookStatusKind), nullable=False)
    )
    acquired_at: datetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )
    notes: str | None = Field(default=None)
    lent_to_user_id: uuid.UUID | None = Field(
        default=None, foreign_key="user.id", index=True
    )
    lent_to_name: str | None = Field(default=None, max_length=255)
    lent_at: datetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )
    returned_at: datetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )

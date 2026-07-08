import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, Column, DateTime, UniqueConstraint
from sqlmodel import Field, SQLModel

from app.models.mixins import IdMixin, TimestampMixin


class ChatThread(SQLModel, IdMixin, TimestampMixin, table=True):
    """Direct messaging thread between two users (always sorted by user ID)."""

    __table_args__ = (
        UniqueConstraint("user_a_id", "user_b_id", name="uq_chat_thread_users"),
        CheckConstraint("user_a_id < user_b_id", name="ck_chat_thread_user_order"),
    )

    user_a_id: uuid.UUID = Field(foreign_key="user.id", index=True)
    user_b_id: uuid.UUID = Field(foreign_key="user.id", index=True)
    last_message_at: datetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )


class ChatMessage(SQLModel, IdMixin, TimestampMixin, table=True):
    """Message within a chat thread, with optional book/collection attachment."""

    thread_id: uuid.UUID = Field(foreign_key="chatthread.id", index=True)
    sender_id: uuid.UUID = Field(foreign_key="user.id", index=True)
    body: str = Field(nullable=False)
    attachment_book_id: uuid.UUID | None = Field(
        default=None, foreign_key="book.id", index=True
    )
    attachment_collection_id: uuid.UUID | None = Field(
        default=None, foreign_key="collection.id", index=True
    )
    read_at: datetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )

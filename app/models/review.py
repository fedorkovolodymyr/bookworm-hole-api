import uuid

from sqlalchemy import CheckConstraint, UniqueConstraint
from sqlmodel import Field, SQLModel

from app.models.mixins import IdMixin, TimestampMixin


class Review(SQLModel, IdMixin, TimestampMixin, table=True):
    __table_args__ = (
        CheckConstraint(
            "(book_id IS NOT NULL AND release_id IS NULL) OR "
            "(book_id IS NULL AND release_id IS NOT NULL)",
            name="ck_review_exactly_one_target",
        ),
        CheckConstraint(
            "rating IS NULL OR (rating >= 1 AND rating <= 5)",
            name="ck_review_rating_range",
        ),
        UniqueConstraint("user_id", "book_id", name="uq_review_user_book"),
        UniqueConstraint("user_id", "release_id", name="uq_review_user_release"),
    )

    user_id: uuid.UUID = Field(foreign_key="user.id", index=True)
    book_id: uuid.UUID | None = Field(default=None, foreign_key="book.id", index=True)
    release_id: uuid.UUID | None = Field(
        default=None, foreign_key="releases.id", index=True
    )
    rating: int | None = Field(default=None)
    title: str | None = Field(default=None, max_length=255)
    body: str | None = Field(default=None)
    is_public: bool = Field(default=True)
    contains_spoilers: bool = Field(default=False)

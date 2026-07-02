import uuid
from typing import TYPE_CHECKING

from sqlmodel import Field, Relationship, SQLModel

from app.models.mixins import IdMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.books import Book


class Release(SQLModel, IdMixin, TimestampMixin, table=True):
    __tablename__ = "releases"

    isbn: str = Field(max_length=20, unique=True, index=True)
    book_id: uuid.UUID = Field(foreign_key="book.id", index=True)

    book: "Book" = Relationship(back_populates="releases")

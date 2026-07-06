import enum
import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, Index, func
from sqlalchemy import Enum as SAEnum
from sqlmodel import Field, Relationship, SQLModel

from app.models.mixins import IdMixin, TimestampMixin


class ContributorRole(str, enum.Enum):
    author = "author"
    co_author = "co_author"
    translator = "translator"
    illustrator = "illustrator"
    editor = "editor"
    narrator = "narrator"
    foreword = "foreword"
    other = "other"


class ReleaseFormat(str, enum.Enum):
    hardcover = "hardcover"
    paperback = "paperback"
    ebook = "ebook"
    audiobook = "audiobook"
    other = "other"


class ISBNKind(str, enum.Enum):
    isbn10 = "isbn10"
    isbn13 = "isbn13"
    asin = "asin"
    other = "other"


class BookContributor(SQLModel, table=True):
    __tablename__ = "book_contributors"

    book_id: uuid.UUID = Field(foreign_key="book.id", primary_key=True)
    contributor_id: uuid.UUID = Field(foreign_key="contributors.id", primary_key=True)
    role: ContributorRole = Field(
        sa_column=Column(SAEnum(ContributorRole), primary_key=True, nullable=False)
    )


class ReleaseContributor(SQLModel, table=True):
    __tablename__ = "release_contributors"

    release_id: uuid.UUID = Field(foreign_key="releases.id", primary_key=True)
    contributor_id: uuid.UUID = Field(foreign_key="contributors.id", primary_key=True)
    role: ContributorRole = Field(
        sa_column=Column(SAEnum(ContributorRole), primary_key=True, nullable=False)
    )


class Book(SQLModel, IdMixin, TimestampMixin, table=True):
    title: str = Field(max_length=255, index=True)
    original_title: str | None = Field(default=None, max_length=255)
    original_language: str | None = Field(default=None, max_length=35)
    first_publication_year: int | None = Field(default=None)
    description: str

    releases: list[Release] = Relationship(
        back_populates="book",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
    contributors: list[Contributor] = Relationship(
        back_populates="books", link_model=BookContributor
    )


class Release(SQLModel, IdMixin, TimestampMixin, table=True):
    __tablename__ = "releases"
    __table_args__ = (
        Index("ix_releases_book_id_format_language", "book_id", "format", "language"),
    )

    book_id: uuid.UUID = Field(foreign_key="book.id", index=True)
    format: ReleaseFormat = Field(
        sa_column=Column(SAEnum(ReleaseFormat), nullable=False)
    )
    publisher: str = Field(max_length=255)
    published_year: int | None = Field(default=None)
    language: str = Field(max_length=35)
    page_count: int | None = Field(default=None)
    duration_minutes: int | None = Field(default=None)
    cover_image_url: str | None = Field(default=None, max_length=2048)
    description_override: str | None = Field(default=None)
    last_external_sync_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )

    book: Book = Relationship(back_populates="releases")
    isbns: list[ISBN] = Relationship(
        back_populates="release",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
    contributors: list[Contributor] = Relationship(
        back_populates="releases", link_model=ReleaseContributor
    )


class ISBN(SQLModel, IdMixin, table=True):
    __tablename__ = "isbns"

    release_id: uuid.UUID = Field(foreign_key="releases.id", index=True)
    code_normalized: str = Field(max_length=20, unique=True, index=True)
    code_original: str = Field(max_length=32)
    kind: ISBNKind = Field(sa_column=Column(SAEnum(ISBNKind), nullable=False))
    created_at: datetime = Field(
        sa_column=Column(
            DateTime(timezone=True),
            server_default=func.now(),
            nullable=False,
            index=True,
        )
    )

    release: Release = Relationship(back_populates="isbns")


class Contributor(SQLModel, IdMixin, TimestampMixin, table=True):
    __tablename__ = "contributors"

    full_name: str = Field(max_length=255, index=True)
    sort_name: str = Field(max_length=255, index=True)
    birth_year: int | None = Field(default=None)
    death_year: int | None = Field(default=None)
    bio: str | None = Field(default=None)
    slug: str = Field(max_length=255, unique=True, index=True)

    books: list[Book] = Relationship(
        back_populates="contributors", link_model=BookContributor
    )
    releases: list[Release] = Relationship(
        back_populates="contributors", link_model=ReleaseContributor
    )

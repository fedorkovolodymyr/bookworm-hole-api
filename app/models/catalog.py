import enum
import uuid

from sqlalchemy import Column
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

    releases: list["Release"] = Relationship(back_populates="book")
    contributors: list["Contributor"] = Relationship(
        back_populates="books", link_model=BookContributor
    )


class Release(SQLModel, IdMixin, TimestampMixin, table=True):
    __tablename__ = "releases"

    isbn: str = Field(max_length=20, unique=True, index=True)
    book_id: uuid.UUID = Field(foreign_key="book.id", index=True)

    book: Book = Relationship(back_populates="releases")


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

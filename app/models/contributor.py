import enum
import uuid

from sqlalchemy import Column
from sqlalchemy import Enum as SAEnum
from sqlmodel import Field, SQLModel

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


class Contributor(SQLModel, IdMixin, TimestampMixin, table=True):
    __tablename__ = "contributors"

    full_name: str = Field(max_length=255, index=True)
    sort_name: str = Field(max_length=255, index=True)
    birth_year: int | None = Field(default=None)
    death_year: int | None = Field(default=None)
    bio: str | None = Field(default=None)
    slug: str = Field(max_length=255, unique=True, index=True)


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

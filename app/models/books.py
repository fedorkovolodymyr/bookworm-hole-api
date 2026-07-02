from typing import TYPE_CHECKING

from sqlmodel import Field, Relationship, SQLModel

from app.models.contributor import BookContributor
from app.models.mixins import IdMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.contributor import Contributor
    from app.models.releases import Release


class Book(SQLModel, IdMixin, TimestampMixin, table=True):
    title: str = Field(max_length=255, index=True)
    original_title: str | None = Field(default=None, max_length=255)
    original_language: str | None = Field(default=None, max_length=35)
    first_publication_year: int | None = Field(default=None)
    description: str
    slug: str = Field(max_length=255, unique=True, index=True)

    releases: list["Release"] = Relationship(back_populates="book")
    contributors: list["Contributor"] = Relationship(
        back_populates="books", link_model=BookContributor
    )

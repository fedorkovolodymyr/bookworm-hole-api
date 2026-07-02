from sqlmodel import Field, SQLModel

from app.models.mixins import IdMixin, TimestampMixin


class Release(SQLModel, IdMixin, TimestampMixin, table=True):
    __tablename__ = "releases"

    isbn: str = Field(max_length=20, unique=True, index=True)

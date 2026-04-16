from sqlmodel import Field, SQLModel

from app.models.mixins import IdMixin, TimestampMixin


class Book(SQLModel, IdMixin, TimestampMixin, table=True):
    title: str = Field(max_length=255, index=True)
    description: str

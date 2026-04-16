from sqlalchemy import Column, String
from sqlmodel import SQLModel

from app.models.mixins import IdMixin, TimestampMixin


class Release(SQLModel, table=True, mixins=(IdMixin, TimestampMixin)):
    __tablename__ = "releases"

    isbn = Column(String, unique=True, nullable=False)

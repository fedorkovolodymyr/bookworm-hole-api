from sqlalchemy import Column, String

from app.models.base import Base, IdMixin


class Book(Base, IdMixin):
    __tablename__ = "books"

    name = Column(String)

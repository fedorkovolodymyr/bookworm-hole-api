from sqlalchemy import Column, String

from app.models.base import Base, IdMixin


class Hero(Base, IdMixin):
    name = Column(String)

from babel import Locale, UnknownLocaleError
from pydantic import field_validator
from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import CITEXT
from sqlmodel import Field, SQLModel

from app.models.mixins import IdMixin, TimestampMixin


class User(SQLModel, IdMixin, TimestampMixin, table=True):
    email: str = Field(sa_column=Column(CITEXT, unique=True, nullable=False))
    username: str = Field(sa_column=Column(CITEXT, unique=True, nullable=False))
    password_hash: str | None = Field(default=None)
    display_name: str = Field(max_length=255)
    avatar_url: str | None = Field(default=None)
    bio: str | None = Field(default=None)
    locale: str = Field(default="en", max_length=10)
    timezone: str = Field(default="UTC", max_length=64)
    is_active: bool = Field(default=True)
    is_admin: bool = Field(default=False)

    @field_validator("locale")
    @classmethod
    def validate_locale(cls, value: str) -> str:
        try:
            Locale.parse(value, sep="-")
        except (UnknownLocaleError, ValueError) as exc:
            raise ValueError(f"'{value}' is not a valid ISO locale") from exc
        return value

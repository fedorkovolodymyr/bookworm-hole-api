from datetime import datetime
from typing import Annotated

from babel import Locale as BabelLocale
from babel import UnknownLocaleError
from pydantic import AfterValidator
from sqlalchemy import Column, DateTime
from sqlalchemy.dialects.postgresql import CITEXT
from sqlmodel import Field, SQLModel

from app.models.mixins import IdMixin, TimestampMixin


def _validate_bcp47_locale(value: str) -> str:
    try:
        BabelLocale.parse(value, sep="-")
    except (UnknownLocaleError, ValueError) as exc:
        raise ValueError(f"'{value}' is not a valid BCP-47 locale") from exc
    return value


Locale = Annotated[str, AfterValidator(_validate_bcp47_locale)]


class User(SQLModel, IdMixin, TimestampMixin, table=True):
    email: str = Field(sa_column=Column(CITEXT, unique=True, nullable=False))
    username: str = Field(sa_column=Column(CITEXT, unique=True, nullable=False))
    password_hash: str | None = Field(default=None)
    display_name: str = Field(max_length=255)
    avatar_url: str | None = Field(default=None)
    bio: str | None = Field(default=None)
    locale: Locale = Field(default="en", max_length=10)
    timezone: str = Field(default="UTC", max_length=64)
    is_active: bool = Field(default=True)
    is_admin: bool = Field(default=False)
    deletion_scheduled_at: datetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )

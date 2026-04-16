import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, func
from sqlalchemy.orm import declarative_mixin
from sqlmodel import Field


@declarative_mixin
class IdMixin:
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)


@declarative_mixin
class TimestampMixin:
    created_at: datetime = Field(
        sa_column=Column(
            DateTime(timezone=True),
            server_default=func.now(),
            nullable=False,
            index=True,
        )
    )
    updated_at: datetime = Field(
        sa_column=Column(
            DateTime(timezone=True),
            server_default=func.now(),
            onupdate=func.now(),
            nullable=False,
        )
    )

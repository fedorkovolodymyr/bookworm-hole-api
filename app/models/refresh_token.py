from datetime import datetime
from uuid import UUID

from sqlalchemy import Column, DateTime, ForeignKey
from sqlmodel import Field, SQLModel

from app.models.mixins import IdMixin, TimestampMixin


class RefreshToken(SQLModel, IdMixin, TimestampMixin, table=True):
    user_id: UUID = Field(
        sa_column=Column(
            ForeignKey("user.id", ondelete="CASCADE"), nullable=False, index=True
        )
    )
    jti: str = Field(unique=True, index=True, max_length=64)
    expires_at: datetime = Field(sa_column=Column(DateTime(timezone=True)))
    revoked_at: datetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )

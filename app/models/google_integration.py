from datetime import datetime
from uuid import UUID

from sqlalchemy import ARRAY, Column, DateTime, ForeignKey, String
from sqlmodel import Field, SQLModel

from app.models.mixins import IdMixin, TimestampMixin


class GoogleIntegration(SQLModel, IdMixin, TimestampMixin, table=True):
    user_id: UUID = Field(
        sa_column=Column(
            ForeignKey("user.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
            index=True,
        )
    )
    access_token_encrypted: str
    refresh_token_encrypted: str
    # Service always stores/compares these as timezone-aware (datetime.now(UTC));
    # the column must match or asyncpg rejects the insert.
    expires_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False)
    )
    scopes: list[str] = Field(sa_column=Column(ARRAY(String), nullable=False))
    connected_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False)
    )

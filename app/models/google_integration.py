from datetime import datetime
from uuid import UUID

from sqlalchemy import ARRAY, Column, ForeignKey, String
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
    expires_at: datetime
    scopes: list[str] = Field(sa_column=Column(ARRAY(String), nullable=False))
    connected_at: datetime

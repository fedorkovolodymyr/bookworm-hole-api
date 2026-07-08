import enum
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Column, DateTime, func
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel

from app.models.mixins import IdMixin


class EntityType(str, enum.Enum):
    book = "book"
    release = "release"
    contributor = "contributor"


class ChangeSource(str, enum.Enum):
    admin = "admin"
    contribution = "contribution"
    external_sync = "external_sync"
    system = "system"


class EntityVersion(SQLModel, IdMixin, table=True):
    """Immutable snapshot of a Book/Release/Contributor recorded on every mutation.

    Recorded automatically via SQLAlchemy `after_insert`/`after_update` listeners
    (see `app/services/entity_version_listeners.py`) rather than explicit calls
    scattered through service methods.
    """

    __tablename__ = "entity_versions"

    entity_type: EntityType = Field(
        sa_column=Column(SAEnum(EntityType), nullable=False, index=True)
    )
    entity_id: uuid.UUID = Field(index=True)
    version_number: int = Field()
    snapshot: dict[str, Any] = Field(sa_column=Column(JSONB, nullable=False))
    changed_by_user_id: uuid.UUID | None = Field(
        default=None, foreign_key="user.id", index=True
    )
    change_source: ChangeSource = Field(
        sa_column=Column(SAEnum(ChangeSource), nullable=False)
    )
    contribution_id: uuid.UUID | None = Field(
        default=None, foreign_key="contribution.id", index=True
    )
    created_at: datetime = Field(
        sa_column=Column(
            DateTime(timezone=True),
            server_default=func.now(),
            nullable=False,
            index=True,
        )
    )

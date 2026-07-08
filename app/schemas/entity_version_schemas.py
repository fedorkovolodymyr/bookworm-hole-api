from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.entity_version import ChangeSource, EntityType


class EntityVersionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    entity_type: EntityType
    entity_id: UUID
    version_number: int
    changed_by_user_id: UUID | None
    change_source: ChangeSource
    contribution_id: UUID | None
    created_at: datetime


class EntityVersionDetailResponse(EntityVersionResponse):
    snapshot: dict[str, Any]

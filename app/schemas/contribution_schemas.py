from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.contribution import ContributionKind, ContributionStatus


class CreateContributionSchema(BaseModel):
    kind: ContributionKind
    target_id: UUID | None = None
    payload: dict[str, Any]


class UpdateContributionSchema(BaseModel):
    payload: dict[str, Any]


class ContributionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    kind: ContributionKind
    target_id: UUID | None
    payload: dict[str, Any]
    status: ContributionStatus
    reviewer_id: UUID | None
    review_notes: str | None
    created_at: datetime
    updated_at: datetime

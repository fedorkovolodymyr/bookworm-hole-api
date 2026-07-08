import enum
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Column, DateTime, func
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel

from app.models.mixins import IdMixin


class AuditAction(str, enum.Enum):
    approve_contribution = "approve_contribution"
    reject_contribution = "reject_contribution"
    claim_contribution = "claim_contribution"
    activate_user = "activate_user"
    deactivate_user = "deactivate_user"
    promote_user = "promote_user"
    demote_user = "demote_user"


class AuditTargetType(str, enum.Enum):
    contribution = "contribution"
    user = "user"


class AuditLog(SQLModel, IdMixin, table=True):
    """Append-only log of sensitive admin actions.

    actor_id is FK-less to preserve audit trail after GDPR user deletion.
    created_at is indexed for range queries and sorted listing.
    """

    actor_id: uuid.UUID = Field(index=True, nullable=False)
    action: AuditAction = Field(sa_column=Column(SAEnum(AuditAction), nullable=False))
    target_type: AuditTargetType = Field(
        sa_column=Column(SAEnum(AuditTargetType), nullable=False)
    )
    target_id: uuid.UUID = Field(index=True, nullable=False)
    audit_metadata: dict[str, Any] = Field(
        default_factory=dict, sa_column=Column(JSONB, nullable=False)
    )
    ip_address: str | None = Field(default=None)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(
            DateTime(timezone=True),
            server_default=func.now(),
            nullable=False,
            index=True,
        ),
    )

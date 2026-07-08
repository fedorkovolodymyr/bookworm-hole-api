from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel

from app.models.audit_log import AuditAction, AuditTargetType


class AuditLogResponse(BaseModel):
    id: UUID
    actor_id: UUID
    action: AuditAction
    target_type: AuditTargetType
    target_id: UUID
    audit_metadata: dict[str, Any]
    ip_address: str | None
    created_at: datetime

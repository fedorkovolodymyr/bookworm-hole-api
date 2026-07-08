from datetime import datetime
from typing import Any
from uuid import UUID

from app.models.audit_log import AuditAction, AuditLog, AuditTargetType
from app.repositories.audit_log_repository import AuditLogRepository
from app.schemas.audit_log_schemas import AuditLogResponse
from app.schemas.common_schemas import Page


class AuditLogService:
    def __init__(self, repository: AuditLogRepository) -> None:
        self.repository = repository

    async def record(
        self,
        actor_id: UUID,
        action: AuditAction,
        target_type: AuditTargetType,
        target_id: UUID,
        audit_metadata: dict[str, Any] | None = None,
        ip_address: str | None = None,
    ) -> AuditLog:
        """Record a sensitive admin action to the audit log."""
        log = AuditLog(
            actor_id=actor_id,
            action=action,
            target_type=target_type,
            target_id=target_id,
            audit_metadata=audit_metadata or {},
            ip_address=ip_address,
        )
        return await self.repository.create(log)

    async def list_logs(
        self,
        skip: int = 0,
        limit: int = 10,
        actor_id: UUID | None = None,
        action: AuditAction | None = None,
        target_type: AuditTargetType | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> Page[AuditLogResponse]:
        """List audit logs with optional filters."""
        logs, total = await self.repository.list_logs(
            skip=skip,
            limit=limit,
            actor_id=actor_id,
            action=action,
            target_type=target_type,
            start_date=start_date,
            end_date=end_date,
        )

        return Page(
            items=[AuditLogResponse.model_validate(log) for log in logs],
            total=total,
            limit=limit,
            offset=skip,
        )

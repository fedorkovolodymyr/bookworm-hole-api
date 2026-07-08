from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.deps import require_admin
from app.models.audit_log import AuditAction, AuditTargetType
from app.models.user import User
from app.repositories.audit_log_repository import AuditLogRepository
from app.routers.responses import ADMIN_RESPONSES
from app.schemas.audit_log_schemas import AuditLogResponse
from app.schemas.common_schemas import Page
from app.services.audit_log_service import AuditLogService

admin_audit_logs_router = APIRouter(
    prefix="/admin/audit-logs", tags=["admin"], dependencies=[Depends(require_admin)]
)


def get_audit_log_service(
    session: AsyncSession = Depends(get_session),
) -> AuditLogService:
    return AuditLogService(AuditLogRepository(session))


@admin_audit_logs_router.get(
    "/",
    response_model=Page[AuditLogResponse],
    responses=ADMIN_RESPONSES,
)
async def list_audit_logs(
    skip: int = 0,
    limit: int = 10,
    actor_id: UUID | None = None,
    action: AuditAction | None = None,
    target_type: AuditTargetType | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    service: AuditLogService = Depends(get_audit_log_service),
    current_user: User = Depends(require_admin),
) -> Page[AuditLogResponse]:
    """List audit logs of sensitive admin actions.

    Optional filters:
    - actor_id: Filter by admin who performed the action
    - action: Filter by action type
    - target_type: Filter by target entity type (contribution or user)
    - start_date: Filter by start date (inclusive)
    - end_date: Filter by end date (inclusive)
    """
    return await service.list_logs(
        skip=skip,
        limit=limit,
        actor_id=actor_id,
        action=action,
        target_type=target_type,
        start_date=start_date,
        end_date=end_date,
    )

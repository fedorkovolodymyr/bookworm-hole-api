from collections.abc import Sequence
from datetime import datetime
from uuid import UUID

from sqlalchemy import ColumnElement, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col, select

from app.models.audit_log import AuditAction, AuditLog, AuditTargetType


class AuditLogRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, log: AuditLog) -> AuditLog:
        self.session.add(log)
        await self.session.flush()
        await self.session.refresh(log)
        return log

    async def list_logs(
        self,
        skip: int = 0,
        limit: int = 10,
        actor_id: UUID | None = None,
        action: AuditAction | None = None,
        target_type: AuditTargetType | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> tuple[Sequence[AuditLog], int]:
        filters: list[ColumnElement[bool]] = []

        if actor_id:
            filters.append(col(AuditLog.actor_id) == actor_id)
        if action:
            filters.append(col(AuditLog.action) == action)
        if target_type:
            filters.append(col(AuditLog.target_type) == target_type)
        if start_date:
            filters.append(col(AuditLog.created_at) >= start_date)
        if end_date:
            filters.append(col(AuditLog.created_at) <= end_date)

        base_query = select(AuditLog).order_by(col(AuditLog.created_at).desc())
        count_query = select(func.count(col(AuditLog.id)))

        for condition in filters:
            base_query = base_query.where(condition)
            count_query = count_query.where(condition)

        total_result = await self.session.execute(count_query)
        total = total_result.scalar() or 0

        result = await self.session.execute(base_query.offset(skip).limit(limit))
        logs = result.scalars().all()

        return logs, total

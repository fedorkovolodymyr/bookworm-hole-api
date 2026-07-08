from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col, select

from app.models.backup_record import BackupRecord


class BackupRecordRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self, user_id: UUID, drive_file_id: str, filename: str
    ) -> BackupRecord:
        record = BackupRecord(
            user_id=user_id, drive_file_id=drive_file_id, filename=filename
        )
        self.session.add(record)
        await self.session.commit()
        await self.session.refresh(record)
        return record

    async def get_all_for_user(
        self, user_id: UUID, skip: int = 0, limit: int = 10
    ) -> tuple[Sequence[BackupRecord], int]:
        filters = [col(BackupRecord.user_id) == user_id]
        count_query = select(func.count()).select_from(
            select(BackupRecord.id).where(*filters).subquery()
        )
        total = (await self.session.execute(count_query)).scalar_one()

        query = (
            select(BackupRecord)
            .where(*filters)
            .order_by(col(BackupRecord.created_at).desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(query)
        return result.scalars().all(), total

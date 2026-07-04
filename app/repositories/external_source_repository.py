from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col, select

from app.models.external_source import ExternalRefKind, ExternalSourceRecord


class ExternalSourceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        source: str,
        ref_kind: ExternalRefKind,
        ref: str,
        payload: dict[str, Any],
    ) -> ExternalSourceRecord:
        record = ExternalSourceRecord(
            source=source, ref_kind=ref_kind, ref=ref, payload=payload
        )
        self.session.add(record)
        await self.session.commit()
        await self.session.refresh(record)
        return record

    async def get_by_source_and_ref(
        self, source: str, ref_kind: ExternalRefKind, ref: str
    ) -> ExternalSourceRecord | None:
        result = await self.session.execute(
            select(ExternalSourceRecord)
            .where(col(ExternalSourceRecord.source) == source)
            .where(col(ExternalSourceRecord.ref_kind) == ref_kind)
            .where(col(ExternalSourceRecord.ref) == ref)
            .order_by(col(ExternalSourceRecord.created_at).desc())
        )
        return result.scalars().first()

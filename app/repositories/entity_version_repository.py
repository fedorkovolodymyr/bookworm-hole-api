from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col, select

from app.models.entity_version import EntityType, EntityVersion


class EntityVersionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_by_entity(
        self, entity_type: EntityType, entity_id: UUID, skip: int = 0, limit: int = 10
    ) -> tuple[Sequence[EntityVersion], int]:
        count_query = select(func.count()).select_from(
            select(EntityVersion.id)
            .where(col(EntityVersion.entity_type) == entity_type)
            .where(col(EntityVersion.entity_id) == entity_id)
            .subquery()
        )
        total = (await self.session.execute(count_query)).scalar_one()
        query = (
            select(EntityVersion)
            .where(col(EntityVersion.entity_type) == entity_type)
            .where(col(EntityVersion.entity_id) == entity_id)
            .order_by(col(EntityVersion.version_number).desc())
        )
        result = await self.session.execute(query.offset(skip).limit(limit))
        return result.scalars().all(), total

    async def get_version(
        self, entity_type: EntityType, entity_id: UUID, version_number: int
    ) -> EntityVersion | None:
        query = (
            select(EntityVersion)
            .where(col(EntityVersion.entity_type) == entity_type)
            .where(col(EntityVersion.entity_id) == entity_id)
            .where(col(EntityVersion.version_number) == version_number)
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

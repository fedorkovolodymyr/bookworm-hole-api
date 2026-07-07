from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col, select

from app.models.contribution import Contribution, ContributionStatus
from app.schemas.contribution_schemas import UpdateContributionSchema


class ContributionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, contribution: Contribution) -> Contribution:
        self.session.add(contribution)
        await self.session.commit()
        await self.session.refresh(contribution)
        return contribution

    async def get_by_id(self, contribution_id: UUID) -> Contribution | None:
        return await self.session.get(
            Contribution, contribution_id, populate_existing=True
        )

    async def update(
        self, contribution_id: UUID, data: UpdateContributionSchema
    ) -> Contribution | None:
        contribution = await self.session.get(Contribution, contribution_id)
        if not contribution:
            return None
        contribution.sqlmodel_update(data.model_dump(exclude_unset=True))
        self.session.add(contribution)
        await self.session.commit()
        await self.session.refresh(contribution)
        return contribution

    async def delete(self, contribution_id: UUID) -> bool:
        contribution = await self.session.get(Contribution, contribution_id)
        if not contribution:
            return False
        await self.session.delete(contribution)
        await self.session.commit()
        return True

    async def update_status(
        self, contribution_id: UUID, new_status: ContributionStatus
    ) -> Contribution | None:
        contribution = await self.session.get(Contribution, contribution_id)
        if not contribution:
            return None
        contribution.status = new_status
        self.session.add(contribution)
        await self.session.commit()
        await self.session.refresh(contribution)
        return contribution

    async def list_by_user(
        self, user_id: UUID, skip: int = 0, limit: int = 10
    ) -> tuple[Sequence[Contribution], int]:
        count_query = select(func.count()).select_from(
            select(Contribution.id)
            .where(col(Contribution.user_id) == user_id)
            .subquery()
        )
        total = (await self.session.execute(count_query)).scalar_one()
        query = (
            select(Contribution)
            .where(col(Contribution.user_id) == user_id)
            .order_by(col(Contribution.created_at).desc())
        )
        result = await self.session.execute(query.offset(skip).limit(limit))
        return result.scalars().all(), total

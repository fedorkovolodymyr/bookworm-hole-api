from abc import ABC
from typing import Generic, TypeVar

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base import Base

ModelT = TypeVar("ModelT", bound=Base)


class BaseService(ABC, Generic[ModelT]):
    model: type[ModelT]

    async def get_all(self, session: AsyncSession) -> list[ModelT]:
        stmt = select(self.model)
        result = await session.execute(stmt)
        return list(result.scalars().all())

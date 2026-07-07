from collections.abc import Sequence
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col, select

from app.models.reading_session import ReadingSession


class ReadingSessionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, session: ReadingSession) -> ReadingSession:
        self.session.add(session)
        await self.session.commit()
        await self.session.refresh(session)
        return session

    async def get_by_id(self, session_id: UUID) -> ReadingSession | None:
        return await self.session.get(
            ReadingSession, session_id, populate_existing=True
        )

    async def get_all_for_user(self, user_id: UUID) -> Sequence[ReadingSession]:
        query = select(ReadingSession).where(col(ReadingSession.user_id) == user_id)
        result = await self.session.execute(query)
        return result.scalars().all()

    async def delete(self, session_id: UUID) -> bool:
        session = await self.session.get(ReadingSession, session_id)
        if not session:
            return False
        await self.session.delete(session)
        await self.session.commit()
        return True

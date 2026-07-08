from collections.abc import Sequence
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col, select

from app.models.reading_session import ReadingSession
from app.schemas.reading_session_schemas import UpdateReadingSessionSchema


class ReadingSessionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, reading_session: ReadingSession) -> ReadingSession:
        self.session.add(reading_session)
        await self.session.commit()
        await self.session.refresh(reading_session)
        return reading_session

    async def get_by_id(self, session_id: UUID) -> ReadingSession | None:
        return await self.session.get(ReadingSession, session_id)

    async def get_active_for_user(self, user_id: UUID) -> Sequence[ReadingSession]:
        query = select(ReadingSession).where(
            col(ReadingSession.user_id) == user_id,
            col(ReadingSession.ended_at).is_(None),
        )
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_active_for_user_and_release(
        self, user_id: UUID, release_id: UUID
    ) -> ReadingSession | None:
        query = select(ReadingSession).where(
            col(ReadingSession.user_id) == user_id,
            col(ReadingSession.release_id) == release_id,
            col(ReadingSession.ended_at).is_(None),
        )
        result = await self.session.execute(query)
        return result.scalars().first()

    async def get_sessions_for_user(
        self, user_id: UUID, release_id: UUID | None = None
    ) -> Sequence[ReadingSession]:
        query = select(ReadingSession).where(col(ReadingSession.user_id) == user_id)
        if release_id:
            query = query.where(col(ReadingSession.release_id) == release_id)
        result = await self.session.execute(query)
        return result.scalars().all()

    async def update(
        self, session_id: UUID, data: UpdateReadingSessionSchema
    ) -> ReadingSession | None:
        reading_session = await self.session.get(ReadingSession, session_id)
        if not reading_session:
            return None
        reading_session.sqlmodel_update(data.model_dump(exclude_unset=True))
        self.session.add(reading_session)
        await self.session.commit()
        await self.session.refresh(reading_session)
        return reading_session

    async def save(self, reading_session: ReadingSession) -> ReadingSession:
        self.session.add(reading_session)
        await self.session.commit()
        await self.session.refresh(reading_session)
        return reading_session

    async def delete(self, session_id: UUID) -> bool:
        reading_session = await self.session.get(ReadingSession, session_id)
        if not reading_session:
            return False
        await self.session.delete(reading_session)
        await self.session.commit()
        return True

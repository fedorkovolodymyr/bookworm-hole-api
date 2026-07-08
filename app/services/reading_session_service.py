from collections.abc import Sequence
from datetime import UTC, datetime
from uuid import UUID

from app.core.errors import ConflictError, ErrorMessages, NotFoundError
from app.models.reading_session import ReadingSession
from app.repositories.reading_session_repository import ReadingSessionRepository
from app.schemas.reading_session_schemas import (
    CreateReadingSessionSchema,
    StopReadingSessionSchema,
    UpdateReadingSessionSchema,
)


class ReadingSessionService:
    def __init__(self, repository: ReadingSessionRepository):
        self.repository = repository

    async def start_session(
        self, user_id: UUID, data: CreateReadingSessionSchema
    ) -> ReadingSession:
        existing = await self.repository.get_active_for_user_and_release(
            user_id, data.release_id
        )
        if existing:
            raise ConflictError(ErrorMessages.READING_SESSION_ALREADY_ACTIVE)

        reading_session = ReadingSession(
            user_id=user_id,
            started_at=datetime.now(UTC),
            **data.model_dump(),
        )
        return await self.repository.create(reading_session)

    async def stop_session(
        self, user_id: UUID, release_id: UUID, data: StopReadingSessionSchema
    ) -> ReadingSession:
        reading_session = await self.repository.get_active_for_user_and_release(
            user_id, release_id
        )
        if not reading_session:
            raise ConflictError(ErrorMessages.READING_SESSION_NOT_ACTIVE)

        reading_session.ended_at = datetime.now(UTC)
        if data.position_end is not None:
            reading_session.position_end = data.position_end
        if data.notes is not None:
            reading_session.notes = data.notes

        return await self.repository.save(reading_session)

    async def list_active_sessions(self, user_id: UUID) -> Sequence[ReadingSession]:
        return await self.repository.get_active_for_user(user_id)

    async def list_sessions(
        self, user_id: UUID, release_id: UUID | None = None
    ) -> Sequence[ReadingSession]:
        return await self.repository.get_sessions_for_user(user_id, release_id)

    async def _retrieve_owned(self, user_id: UUID, session_id: UUID) -> ReadingSession:
        reading_session = await self.repository.get_by_id(session_id)
        if not reading_session or reading_session.user_id != user_id:
            raise NotFoundError(ErrorMessages.READING_SESSION_NOT_FOUND)
        return reading_session

    async def update_session(
        self, user_id: UUID, session_id: UUID, data: UpdateReadingSessionSchema
    ) -> ReadingSession:
        await self._retrieve_owned(user_id, session_id)
        reading_session = await self.repository.update(session_id, data)
        if not reading_session:
            raise NotFoundError(ErrorMessages.READING_SESSION_NOT_FOUND)
        return reading_session

    async def delete_session(self, user_id: UUID, session_id: UUID) -> None:
        await self._retrieve_owned(user_id, session_id)
        deleted = await self.repository.delete(session_id)
        if not deleted:
            raise NotFoundError(ErrorMessages.READING_SESSION_NOT_FOUND)

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.deps import get_current_user
from app.models.user import User
from app.repositories.reading_session_repository import ReadingSessionRepository
from app.schemas.reading_session_schemas import (
    CreateReadingSessionSchema,
    ReadingSessionResponse,
    StopReadingSessionSchema,
    UpdateReadingSessionSchema,
)
from app.services.reading_session_service import ReadingSessionService

reading_sessions_router = APIRouter(prefix="/me/reading", tags=["reading-sessions"])


def get_reading_session_service(
    session: AsyncSession = Depends(get_session),
) -> ReadingSessionService:
    return ReadingSessionService(ReadingSessionRepository(session))


@reading_sessions_router.post(
    "/start", response_model=ReadingSessionResponse, status_code=status.HTTP_201_CREATED
)
async def start_session(
    data: CreateReadingSessionSchema,
    current_user: User = Depends(get_current_user),
    service: ReadingSessionService = Depends(get_reading_session_service),
):
    return await service.start_session(current_user.id, data)


@reading_sessions_router.post(
    "/stop", response_model=ReadingSessionResponse, status_code=status.HTTP_200_OK
)
async def stop_session(
    data: StopReadingSessionSchema,
    current_user: User = Depends(get_current_user),
    service: ReadingSessionService = Depends(get_reading_session_service),
):
    return await service.stop_session(current_user.id, data.release_id, data)


@reading_sessions_router.get(
    "/active",
    response_model=list[ReadingSessionResponse],
    status_code=status.HTTP_200_OK,
)
async def list_active_sessions(
    current_user: User = Depends(get_current_user),
    service: ReadingSessionService = Depends(get_reading_session_service),
):
    return list(await service.list_active_sessions(current_user.id))


@reading_sessions_router.get(
    "/sessions",
    response_model=list[ReadingSessionResponse],
    status_code=status.HTTP_200_OK,
)
async def list_sessions(
    release_id: UUID | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    service: ReadingSessionService = Depends(get_reading_session_service),
):
    return list(await service.list_sessions(current_user.id, release_id))


@reading_sessions_router.patch(
    "/sessions/{session_id}",
    response_model=ReadingSessionResponse,
    status_code=status.HTTP_200_OK,
)
async def update_session(
    session_id: UUID,
    data: UpdateReadingSessionSchema,
    current_user: User = Depends(get_current_user),
    service: ReadingSessionService = Depends(get_reading_session_service),
):
    return await service.update_session(current_user.id, session_id, data)


@reading_sessions_router.delete(
    "/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def delete_session(
    session_id: UUID,
    current_user: User = Depends(get_current_user),
    service: ReadingSessionService = Depends(get_reading_session_service),
) -> None:
    await service.delete_session(current_user.id, session_id)

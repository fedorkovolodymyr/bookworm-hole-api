from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.deps import get_current_user
from app.models.book_status import BookStatusKind
from app.models.user import User
from app.repositories.book_status_repository import BookStatusRepository
from app.schemas.book_status_schemas import (
    BookStatusResponse,
    CreateBookStatusSchema,
    LendBookStatusSchema,
    UpdateBookStatusSchema,
)
from app.services.book_status_service import BookStatusService

statuses_router = APIRouter(prefix="/me/statuses", tags=["statuses"])


def get_book_status_service(
    session: AsyncSession = Depends(get_session),
) -> BookStatusService:
    return BookStatusService(BookStatusRepository(session))


@statuses_router.post(
    "/", response_model=BookStatusResponse, status_code=status.HTTP_201_CREATED
)
async def create_status(
    new_status: CreateBookStatusSchema,
    current_user: User = Depends(get_current_user),
    service: BookStatusService = Depends(get_book_status_service),
):
    return await service.create_status(current_user.id, new_status)


@statuses_router.get("/", response_model=list[BookStatusResponse])
async def list_statuses(
    status_filter: BookStatusKind | None = Query(default=None, alias="status"),
    current_user: User = Depends(get_current_user),
    service: BookStatusService = Depends(get_book_status_service),
):
    return await service.list_statuses(current_user.id, status_filter)


@statuses_router.patch("/{status_id}", response_model=BookStatusResponse)
async def modify_status(
    status_id: UUID,
    updated_status: UpdateBookStatusSchema,
    current_user: User = Depends(get_current_user),
    service: BookStatusService = Depends(get_book_status_service),
):
    return await service.modify_status(current_user.id, status_id, updated_status)


@statuses_router.delete("/{status_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_status(
    status_id: UUID,
    current_user: User = Depends(get_current_user),
    service: BookStatusService = Depends(get_book_status_service),
) -> None:
    await service.delete_status(current_user.id, status_id)


@statuses_router.post("/{status_id}/lend", response_model=BookStatusResponse)
async def lend_status(
    status_id: UUID,
    lend: LendBookStatusSchema,
    current_user: User = Depends(get_current_user),
    service: BookStatusService = Depends(get_book_status_service),
):
    return await service.lend_status(current_user.id, status_id, lend)


@statuses_router.post("/{status_id}/return", response_model=BookStatusResponse)
async def return_status(
    status_id: UUID,
    current_user: User = Depends(get_current_user),
    service: BookStatusService = Depends(get_book_status_service),
):
    return await service.return_status(current_user.id, status_id)

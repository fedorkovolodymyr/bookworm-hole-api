from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.deps import get_current_user
from app.models.book_status import BookStatus, BookStatusKind
from app.models.user import User
from app.repositories.book_status_repository import BookStatusRepository, BookStatusSort
from app.schemas.book_status_schemas import BookStatusResponse
from app.schemas.common_schemas import Page
from app.services.book_status_service import BookStatusService

status_views_router = APIRouter(prefix="/me", tags=["statuses"])


def get_book_status_service(
    session: AsyncSession = Depends(get_session),
) -> BookStatusService:
    return BookStatusService(BookStatusRepository(session))


async def _list_page(
    kind: BookStatusKind,
    sort: BookStatusSort,
    skip: int,
    limit: int,
    current_user: User,
    service: BookStatusService,
) -> Page[BookStatus]:
    return await service.list_page_by_kind(current_user.id, kind, sort, skip, limit)


@status_views_router.get("/library", response_model=Page[BookStatusResponse])
async def list_library(
    sort: BookStatusSort = "acquired_at",
    skip: int = 0,
    limit: int = 10,
    current_user: User = Depends(get_current_user),
    service: BookStatusService = Depends(get_book_status_service),
):
    """All `owned` items for the current user."""
    return await _list_page(
        BookStatusKind.owned, sort, skip, limit, current_user, service
    )


@status_views_router.get("/wishlist", response_model=Page[BookStatusResponse])
async def list_wishlist(
    sort: BookStatusSort = "acquired_at",
    skip: int = 0,
    limit: int = 10,
    current_user: User = Depends(get_current_user),
    service: BookStatusService = Depends(get_book_status_service),
):
    """All `wishlist` items for the current user."""
    return await _list_page(
        BookStatusKind.wishlist, sort, skip, limit, current_user, service
    )


@status_views_router.get("/lent-out", response_model=Page[BookStatusResponse])
async def list_lent_out(
    sort: BookStatusSort = "acquired_at",
    skip: int = 0,
    limit: int = 10,
    current_user: User = Depends(get_current_user),
    service: BookStatusService = Depends(get_book_status_service),
):
    """All `lent_out` items for the current user, including borrower info."""
    return await _list_page(
        BookStatusKind.lent_out, sort, skip, limit, current_user, service
    )


@status_views_router.get("/borrowed", response_model=Page[BookStatusResponse])
async def list_borrowed(
    sort: BookStatusSort = "acquired_at",
    skip: int = 0,
    limit: int = 10,
    current_user: User = Depends(get_current_user),
    service: BookStatusService = Depends(get_book_status_service),
):
    """All `borrowed` items for the current user."""
    return await _list_page(
        BookStatusKind.borrowed, sort, skip, limit, current_user, service
    )

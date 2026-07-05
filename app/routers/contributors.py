from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.deps import require_admin
from app.models.catalog import ContributorRole
from app.repositories.contributor_repository import ContributorRepository
from app.routers.responses import ADMIN_RESPONSES, NOT_FOUND_RESPONSE
from app.schemas.book_schemas import BookResponse
from app.schemas.common_schemas import Page
from app.schemas.contributor_schemas import (
    ContributorDetailResponse,
    ContributorResponse,
    CreateContributorSchema,
    UpdateContributorSchema,
)
from app.services.contributor_service import ContributorService

contributors_router = APIRouter(prefix="/contributors", tags=["contributors"])


def get_contributor_service(
    session: AsyncSession = Depends(get_session),
) -> ContributorService:
    return ContributorService(ContributorRepository(session))


@contributors_router.get("/", response_model=Page[ContributorResponse])
async def retrieve_all_contributors(
    skip: int = 0,
    limit: int = 10,
    name: str | None = None,
    role: ContributorRole | None = None,
    service: ContributorService = Depends(get_contributor_service),
):
    """Search matches either `full_name` or `sort_name` (ILIKE)."""
    return await service.retrieve_all_contributors(skip, limit, name, role)


@contributors_router.post(
    "/",
    response_model=ContributorResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_admin)],
    responses=ADMIN_RESPONSES,
)
async def create_contributor(
    new_contributor: CreateContributorSchema,
    service: ContributorService = Depends(get_contributor_service),
):
    return await service.create_contributor(new_contributor)


@contributors_router.get(
    "/{contributor_id}",
    response_model=ContributorDetailResponse,
    responses=NOT_FOUND_RESPONSE,
)
async def retrieve_contributor_by_id(
    contributor_id: UUID,
    service: ContributorService = Depends(get_contributor_service),
):
    """Detail view with the contributor's books/releases grouped by role."""
    return await service.retrieve_contributor_detail(contributor_id)


@contributors_router.patch(
    "/{contributor_id}",
    response_model=ContributorResponse,
    dependencies=[Depends(require_admin)],
    responses=ADMIN_RESPONSES | NOT_FOUND_RESPONSE,
)
async def modify_contributor(
    contributor_id: UUID,
    updated_contributor: UpdateContributorSchema,
    service: ContributorService = Depends(get_contributor_service),
):
    return await service.modify_contributor(contributor_id, updated_contributor)


@contributors_router.get(
    "/{contributor_id}/books",
    response_model=Page[BookResponse],
    responses=NOT_FOUND_RESPONSE,
)
async def retrieve_contributor_books(
    contributor_id: UUID,
    skip: int = 0,
    limit: int = 10,
    service: ContributorService = Depends(get_contributor_service),
):
    return await service.retrieve_contributor_books(contributor_id, skip, limit)

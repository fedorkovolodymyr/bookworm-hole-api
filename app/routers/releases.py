from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.deps import require_admin
from app.repositories.book_repository import BookRepository
from app.repositories.release_repository import ReleaseRepository
from app.repositories.review_repository import ReviewRepository, ReviewSort
from app.routers.responses import ADMIN_RESPONSES, NOT_FOUND_RESPONSE
from app.schemas.book_schemas import (
    CreateReleaseSchema,
    ReleaseWithISBNsResponse,
    UpdateReleaseSchema,
)
from app.schemas.common_schemas import Page
from app.schemas.contributor_schemas import AddContributorSchema
from app.schemas.review_schemas import ReviewResponse
from app.services.release_service import ReleaseService
from app.services.review_service import ReviewService

releases_router = APIRouter(prefix="/releases", tags=["releases"])


def get_release_service(
    session: AsyncSession = Depends(get_session),
) -> ReleaseService:
    return ReleaseService(
        ReleaseRepository(session), BookRepository(session), ReviewRepository(session)
    )


def get_review_service(
    session: AsyncSession = Depends(get_session),
) -> ReviewService:
    return ReviewService(ReviewRepository(session))


@releases_router.get("/{release_id}", response_model=ReleaseWithISBNsResponse)
async def retrieve_release_by_id(
    release_id: UUID,
    service: ReleaseService = Depends(get_release_service),
):
    return await service.retrieve_release_by_id(release_id)


@releases_router.post(
    "/",
    response_model=ReleaseWithISBNsResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_admin)],
)
async def create_release(
    new_release: CreateReleaseSchema,
    service: ReleaseService = Depends(get_release_service),
):
    return await service.create_release(new_release)


@releases_router.patch(
    "/{release_id}",
    response_model=ReleaseWithISBNsResponse,
    dependencies=[Depends(require_admin)],
)
async def modify_release(
    release_id: UUID,
    updated_release: UpdateReleaseSchema,
    service: ReleaseService = Depends(get_release_service),
):
    return await service.modify_release(release_id, updated_release)


@releases_router.post(
    "/{release_id}/contributors",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_admin)],
    responses=ADMIN_RESPONSES | NOT_FOUND_RESPONSE,
)
async def add_release_contributor(
    release_id: UUID,
    payload: AddContributorSchema,
    service: ReleaseService = Depends(get_release_service),
) -> dict[str, str]:
    """Add a contributor to a release. Returns 200 if already existed, 201 if newly
    created."""
    created = await service.add_contributor(
        release_id, payload.contributor_id, payload.role
    )
    return {"status": "created" if created else "already_existed"}


@releases_router.delete(
    "/{release_id}/contributors/{contributor_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_admin)],
    responses=ADMIN_RESPONSES | NOT_FOUND_RESPONSE,
)
async def remove_release_contributor(
    release_id: UUID,
    contributor_id: UUID,
    role: str,
    service: ReleaseService = Depends(get_release_service),
) -> None:
    from app.models.catalog import ContributorRole

    role_enum = ContributorRole(role)
    await service.remove_contributor(release_id, contributor_id, role_enum)


@releases_router.get("/{release_id}/reviews", response_model=Page[ReviewResponse])
async def retrieve_release_reviews(
    release_id: UUID,
    sort: ReviewSort = "created_at",
    skip: int = 0,
    limit: int = 10,
    service: ReviewService = Depends(get_review_service),
):
    return await service.list_for_release(release_id, sort, skip, limit)

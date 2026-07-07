from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.deps import get_current_user
from app.models.user import User
from app.repositories.contribution_repository import ContributionRepository
from app.schemas.common_schemas import Page
from app.schemas.contribution_schemas import (
    ContributionResponse,
    CreateContributionSchema,
    UpdateContributionSchema,
)
from app.services.contribution_service import ContributionService

contributions_router = APIRouter(prefix="/contributions", tags=["contributions"])


def get_contribution_service(
    session: AsyncSession = Depends(get_session),
) -> ContributionService:
    return ContributionService(ContributionRepository(session))


@contributions_router.post(
    "/", response_model=ContributionResponse, status_code=status.HTTP_201_CREATED
)
async def create_contribution(
    data: CreateContributionSchema,
    current_user: User = Depends(get_current_user),
    service: ContributionService = Depends(get_contribution_service),
):
    return await service.create_contribution(current_user.id, data)


@contributions_router.get(
    "/me/contributions", response_model=Page[ContributionResponse]
)
async def list_own_contributions(
    current_user: User = Depends(get_current_user),
    service: ContributionService = Depends(get_contribution_service),
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
):
    return await service.list_own(current_user.id, skip, limit)


@contributions_router.get("/{contribution_id}", response_model=ContributionResponse)
async def get_contribution(
    contribution_id: UUID,
    current_user: User = Depends(get_current_user),
    service: ContributionService = Depends(get_contribution_service),
):
    return await service.get_contribution(current_user.id, contribution_id)


@contributions_router.patch("/{contribution_id}", response_model=ContributionResponse)
async def update_contribution(
    contribution_id: UUID,
    data: UpdateContributionSchema,
    current_user: User = Depends(get_current_user),
    service: ContributionService = Depends(get_contribution_service),
):
    return await service.update_contribution(current_user.id, contribution_id, data)


@contributions_router.post(
    "/{contribution_id}/submit", response_model=ContributionResponse
)
async def submit_contribution(
    contribution_id: UUID,
    current_user: User = Depends(get_current_user),
    service: ContributionService = Depends(get_contribution_service),
):
    return await service.submit_contribution(current_user.id, contribution_id)


@contributions_router.delete(
    "/{contribution_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def delete_contribution(
    contribution_id: UUID,
    current_user: User = Depends(get_current_user),
    service: ContributionService = Depends(get_contribution_service),
) -> None:
    await service.delete_contribution(current_user.id, contribution_id)

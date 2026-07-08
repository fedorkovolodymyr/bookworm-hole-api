from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.deps import require_admin
from app.models.contribution import ContributionStatus
from app.models.user import User
from app.repositories.contribution_repository import ContributionRepository
from app.routers.responses import ADMIN_RESPONSES, CONFLICT_RESPONSE, NOT_FOUND_RESPONSE
from app.schemas.common_schemas import Page
from app.schemas.contribution_schemas import (
    AdminContributionResponse,
    ContributionDiffResponse,
    RejectContributionSchema,
)
from app.services.contribution_service import ContributionService

admin_contributions_router = APIRouter(
    prefix="/admin/contributions",
    tags=["admin"],
    dependencies=[Depends(require_admin)],
    responses=ADMIN_RESPONSES,
)


def get_contribution_service(
    session: AsyncSession = Depends(get_session),
) -> ContributionService:
    return ContributionService(ContributionRepository(session))


@admin_contributions_router.get(
    "/",
    response_model=Page[AdminContributionResponse],
)
async def list_contributions_by_status(
    status: ContributionStatus = Query(ContributionStatus.submitted),
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    service: ContributionService = Depends(get_contribution_service),
):
    return await service.list_by_status(status, skip, limit)


@admin_contributions_router.post(
    "/{contribution_id}/claim",
    response_model=AdminContributionResponse,
    responses=NOT_FOUND_RESPONSE | CONFLICT_RESPONSE,
)
async def claim_contribution(
    contribution_id: UUID,
    current_user: User = Depends(require_admin),
    service: ContributionService = Depends(get_contribution_service),
):
    return await service.claim_contribution(contribution_id, current_user.id)


@admin_contributions_router.post(
    "/{contribution_id}/approve",
    response_model=AdminContributionResponse,
    responses=NOT_FOUND_RESPONSE | CONFLICT_RESPONSE,
    status_code=status.HTTP_200_OK,
)
async def approve_contribution(
    contribution_id: UUID,
    service: ContributionService = Depends(get_contribution_service),
):
    return await service.approve_contribution(contribution_id)


@admin_contributions_router.post(
    "/{contribution_id}/reject",
    response_model=AdminContributionResponse,
    responses=NOT_FOUND_RESPONSE | CONFLICT_RESPONSE,
)
async def reject_contribution(
    contribution_id: UUID,
    data: RejectContributionSchema,
    service: ContributionService = Depends(get_contribution_service),
):
    return await service.reject_contribution(contribution_id, data.notes)


@admin_contributions_router.get(
    "/{contribution_id}/diff",
    response_model=ContributionDiffResponse,
    responses=NOT_FOUND_RESPONSE,
)
async def get_contribution_diff(
    contribution_id: UUID,
    service: ContributionService = Depends(get_contribution_service),
):
    return await service.get_diff(contribution_id)

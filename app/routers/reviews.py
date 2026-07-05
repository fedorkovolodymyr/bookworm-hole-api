from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.deps import get_current_user
from app.models.user import User
from app.repositories.review_repository import ReviewRepository
from app.schemas.review_schemas import (
    CreateReviewSchema,
    ReviewResponse,
    UpdateReviewSchema,
)
from app.services.review_service import ReviewService

reviews_router = APIRouter(prefix="/reviews", tags=["reviews"])


def get_review_service(
    session: AsyncSession = Depends(get_session),
) -> ReviewService:
    return ReviewService(ReviewRepository(session))


@reviews_router.post(
    "/", response_model=ReviewResponse, status_code=status.HTTP_201_CREATED
)
async def create_review(
    new_review: CreateReviewSchema,
    current_user: User = Depends(get_current_user),
    service: ReviewService = Depends(get_review_service),
):
    return await service.create_review(current_user.id, new_review)


@reviews_router.get("/{review_id}", response_model=ReviewResponse)
async def retrieve_review(
    review_id: UUID,
    current_user: User = Depends(get_current_user),
    service: ReviewService = Depends(get_review_service),
):
    return await service.get_review(current_user.id, review_id)


@reviews_router.patch("/{review_id}", response_model=ReviewResponse)
async def update_review(
    review_id: UUID,
    data: UpdateReviewSchema,
    current_user: User = Depends(get_current_user),
    service: ReviewService = Depends(get_review_service),
):
    return await service.update_review(current_user.id, review_id, data)


@reviews_router.delete("/{review_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_review(
    review_id: UUID,
    current_user: User = Depends(get_current_user),
    service: ReviewService = Depends(get_review_service),
) -> None:
    await service.delete_review(current_user.id, review_id)

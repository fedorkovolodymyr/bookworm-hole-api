from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.repositories.review_repository import ReviewRepository, ReviewSort
from app.schemas.common_schemas import Page
from app.schemas.review_schemas import ReviewResponse
from app.services.review_service import ReviewService

users_router = APIRouter(prefix="/users", tags=["users"])


def get_review_service(
    session: AsyncSession = Depends(get_session),
) -> ReviewService:
    return ReviewService(ReviewRepository(session))


@users_router.get("/{user_id}/reviews", response_model=Page[ReviewResponse])
async def retrieve_user_reviews(
    user_id: UUID,
    sort: ReviewSort = "created_at",
    skip: int = 0,
    limit: int = 10,
    service: ReviewService = Depends(get_review_service),
):
    """List a user's public reviews."""
    return await service.list_public_for_user(user_id, sort, skip, limit)

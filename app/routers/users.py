from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.deps import get_current_user
from app.models.user import User
from app.repositories.collection_repository import CollectionRepository
from app.repositories.review_repository import ReviewRepository, ReviewSort
from app.repositories.user_repository import UserRepository
from app.routers.responses import CONFLICT_RESPONSE
from app.schemas.common_schemas import Page
from app.schemas.review_schemas import ReviewResponse
from app.schemas.user_schemas import (
    ChangePasswordSchema,
    PublicUserProfileResponse,
    UpdateUserSchema,
    UserProfileResponse,
)
from app.services.review_service import ReviewService
from app.services.user_service import UserService

users_router = APIRouter(prefix="/users", tags=["users"])


def get_review_service(
    session: AsyncSession = Depends(get_session),
) -> ReviewService:
    return ReviewService(ReviewRepository(session))


def get_user_service(session: AsyncSession = Depends(get_session)) -> UserService:
    return UserService(UserRepository(session), CollectionRepository(session))


@users_router.get("/me", response_model=UserProfileResponse)
async def retrieve_own_profile(current_user: User = Depends(get_current_user)):
    return current_user


@users_router.patch("/me", response_model=UserProfileResponse)
async def update_own_profile(
    data: UpdateUserSchema,
    current_user: User = Depends(get_current_user),
    service: UserService = Depends(get_user_service),
):
    return await service.update_profile(current_user.id, data)


@users_router.post("/me/password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(
    data: ChangePasswordSchema,
    current_user: User = Depends(get_current_user),
    service: UserService = Depends(get_user_service),
) -> None:
    """Change password. Requires the current password."""
    await service.change_password(current_user.id, data)


@users_router.post("/me/deactivate", response_model=UserProfileResponse)
async def deactivate_own_account(
    current_user: User = Depends(get_current_user),
    service: UserService = Depends(get_user_service),
):
    """Soft-deactivate the account. Reversible by an admin."""
    return await service.deactivate(current_user.id)


@users_router.post("/me/delete", response_model=UserProfileResponse)
async def schedule_own_deletion(
    current_user: User = Depends(get_current_user),
    service: UserService = Depends(get_user_service),
):
    """Schedule account deletion. Hard-deleted after a 30-day grace period."""
    return await service.schedule_deletion(current_user.id)


@users_router.post(
    "/me/delete/cancel",
    response_model=UserProfileResponse,
    responses=CONFLICT_RESPONSE,
)
async def cancel_own_deletion(
    current_user: User = Depends(get_current_user),
    service: UserService = Depends(get_user_service),
):
    """Cancel a scheduled deletion while still within the grace period."""
    return await service.cancel_deletion(current_user.id)


@users_router.get("/{username}", response_model=PublicUserProfileResponse)
async def retrieve_public_profile(
    username: str,
    skip: int = 0,
    limit: int = 10,
    service: UserService = Depends(get_user_service),
):
    """Public profile: display name, bio, and public collections only."""
    return await service.get_public_profile(username, skip, limit)


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

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.deps import require_admin
from app.repositories.collection_repository import CollectionRepository
from app.repositories.password_reset_token_repository import (
    PasswordResetTokenRepository,
)
from app.repositories.user_repository import UserRepository
from app.routers.responses import ADMIN_RESPONSES, NOT_FOUND_RESPONSE
from app.schemas.common_schemas import Page
from app.schemas.user_schemas import AdminUserResponse, PasswordResetTokenResponse
from app.services.user_service import UserService

admin_users_router = APIRouter(
    prefix="/admin/users",
    tags=["admin"],
    dependencies=[Depends(require_admin)],
    responses=ADMIN_RESPONSES,
)


def get_user_service(session: AsyncSession = Depends(get_session)) -> UserService:
    return UserService(
        UserRepository(session),
        CollectionRepository(session),
        PasswordResetTokenRepository(session),
    )


@admin_users_router.get(
    "/",
    response_model=Page[AdminUserResponse],
)
async def list_users(
    skip: int = 0,
    limit: int = 10,
    email: str | None = None,
    username: str | None = None,
    is_active: bool | None = None,
    is_admin: bool | None = None,
    service: UserService = Depends(get_user_service),
):
    return await service.list_users(
        skip=skip,
        limit=limit,
        email=email,
        username=username,
        is_active=is_active,
        is_admin=is_admin,
    )


@admin_users_router.post(
    "/{user_id}/deactivate",
    response_model=AdminUserResponse,
    responses=NOT_FOUND_RESPONSE,
)
async def deactivate_user(
    user_id: UUID,
    service: UserService = Depends(get_user_service),
):
    return await service.deactivate(user_id)


@admin_users_router.post(
    "/{user_id}/activate",
    response_model=AdminUserResponse,
    responses=NOT_FOUND_RESPONSE,
)
async def activate_user(
    user_id: UUID,
    service: UserService = Depends(get_user_service),
):
    return await service.activate_user(user_id)


@admin_users_router.post(
    "/{user_id}/promote",
    response_model=AdminUserResponse,
    responses=NOT_FOUND_RESPONSE,
)
async def promote_user(
    user_id: UUID,
    service: UserService = Depends(get_user_service),
):
    return await service.promote_user(user_id)


@admin_users_router.post(
    "/{user_id}/demote",
    response_model=AdminUserResponse,
    responses=NOT_FOUND_RESPONSE,
)
async def demote_user(
    user_id: UUID,
    service: UserService = Depends(get_user_service),
):
    return await service.demote_user(user_id)


@admin_users_router.post(
    "/{user_id}/password-reset",
    response_model=PasswordResetTokenResponse,
    responses=NOT_FOUND_RESPONSE,
)
async def issue_password_reset(
    user_id: UUID,
    service: UserService = Depends(get_user_service),
):
    return await service.issue_password_reset(user_id)

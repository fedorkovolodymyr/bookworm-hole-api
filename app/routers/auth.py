from fastapi import APIRouter, Depends, status

from app.core.deps import get_auth_service, get_current_user
from app.models.user import User
from app.schemas.auth_schemas import (
    LoginSchema,
    RefreshRequestSchema,
    RegisterResponse,
    RegisterSchema,
    TokenResponse,
    UserResponse,
)
from app.services.auth_service import AuthService

auth_router = APIRouter(prefix="/auth", tags=["auth"])


@auth_router.post(
    "/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED
)
async def register(
    data: RegisterSchema,
    auth_service: AuthService = Depends(get_auth_service),
):
    user, tokens = await auth_service.register(data)
    return RegisterResponse(
        user=UserResponse.model_validate(user),
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
    )


@auth_router.post("/login", response_model=RegisterResponse)
async def login(
    data: LoginSchema,
    auth_service: AuthService = Depends(get_auth_service),
):
    user, tokens = await auth_service.login(data)
    return RegisterResponse(
        user=UserResponse.model_validate(user),
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
    )


@auth_router.post("/refresh", response_model=TokenResponse)
async def refresh(
    data: RefreshRequestSchema,
    auth_service: AuthService = Depends(get_auth_service),
):
    return await auth_service.refresh(data.refresh_token)


@auth_router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    data: RefreshRequestSchema,
    auth_service: AuthService = Depends(get_auth_service),
) -> None:
    await auth_service.logout(data.refresh_token)


@auth_router.get("/me", response_model=UserResponse)
async def me(current_user: User = Depends(get_current_user)):
    return current_user

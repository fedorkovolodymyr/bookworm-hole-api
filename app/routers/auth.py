from fastapi import APIRouter, Depends, status

from app.core.deps import (
    get_auth_service,
    get_current_user,
    get_email_verification_service,
)
from app.models.user import User
from app.routers.responses import AUTH_RESPONSE
from app.schemas.auth_schemas import (
    LoginSchema,
    RefreshRequestSchema,
    RegisterResponse,
    RegisterSchema,
    TokenResponse,
    UserResponse,
    VerifyEmailConfirmSchema,
)
from app.services.auth_service import AuthService
from app.services.email_verification_service import EmailVerificationService

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


@auth_router.post(
    "/verify/request",
    status_code=status.HTTP_202_ACCEPTED,
    responses=AUTH_RESPONSE,
    summary="Request an email verification token for the current user",
)
async def request_email_verification(
    current_user: User = Depends(get_current_user),
    verification_service: EmailVerificationService = Depends(
        get_email_verification_service
    ),
) -> None:
    await verification_service.request_verification(current_user)


@auth_router.post(
    "/verify/confirm",
    response_model=UserResponse,
    summary="Confirm email ownership using a signed verification token",
)
async def confirm_email_verification(
    data: VerifyEmailConfirmSchema,
    verification_service: EmailVerificationService = Depends(
        get_email_verification_service
    ),
) -> UserResponse:
    user = await verification_service.confirm_verification(data.token)
    return UserResponse.model_validate(user)

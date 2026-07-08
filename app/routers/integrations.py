from fastapi import APIRouter, Depends, status
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.deps import get_current_user
from app.models.user import User
from app.repositories.google_integration_repository import GoogleIntegrationRepository
from app.routers.responses import (
    EXTERNAL_SERVICE_RESPONSE,
    NOT_FOUND_RESPONSE,
    UNAUTHORIZED_RESPONSE,
)
from app.schemas.google_integration_schemas import GoogleIntegrationResponse
from app.services.google_integration_service import GoogleIntegrationService

integrations_router = APIRouter(prefix="/integrations", tags=["integrations"])


def get_google_integration_service(
    session: AsyncSession = Depends(get_session),
) -> GoogleIntegrationService:
    return GoogleIntegrationService(GoogleIntegrationRepository(session))


@integrations_router.get(
    "/google/connect",
    summary="Start the Google OAuth flow for Drive access",
    status_code=status.HTTP_307_TEMPORARY_REDIRECT,
)
async def connect_google(
    current_user: User = Depends(get_current_user),
    service: GoogleIntegrationService = Depends(get_google_integration_service),
) -> RedirectResponse:
    authorization_url = service.get_authorization_url(current_user.id)
    return RedirectResponse(
        authorization_url, status_code=status.HTTP_307_TEMPORARY_REDIRECT
    )


@integrations_router.get(
    "/google/callback",
    response_model=GoogleIntegrationResponse,
    summary="Handle the Google OAuth redirect and store encrypted tokens",
    responses=UNAUTHORIZED_RESPONSE | EXTERNAL_SERVICE_RESPONSE,
)
async def google_callback(
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    service: GoogleIntegrationService = Depends(get_google_integration_service),
):
    return await service.handle_callback(code, state, error)


@integrations_router.delete(
    "/google",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoke and clear the caller's Google integration",
    responses=NOT_FOUND_RESPONSE,
)
async def disconnect_google(
    current_user: User = Depends(get_current_user),
    service: GoogleIntegrationService = Depends(get_google_integration_service),
) -> None:
    await service.revoke_and_delete(current_user.id)

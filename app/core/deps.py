from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.db import get_session
from app.models.user import User
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.repositories.user_repository import UserRepository
from app.services.ai.base import AIProvider
from app.services.ai.noop import NoOpAIProvider
from app.services.auth_service import AuthService

bearer_scheme = HTTPBearer()
optional_bearer_scheme = HTTPBearer(auto_error=False)


def get_auth_service(session: AsyncSession = Depends(get_session)) -> AuthService:
    return AuthService(UserRepository(session), RefreshTokenRepository(session))


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    auth_service: AuthService = Depends(get_auth_service),
) -> User:
    return await auth_service.get_current_user(credentials.credentials)


async def get_current_user_optional(
    credentials: HTTPAuthorizationCredentials | None = Depends(optional_bearer_scheme),
    auth_service: AuthService = Depends(get_auth_service),
) -> User | None:
    if credentials is None:
        return None
    return await auth_service.get_current_user(credentials.credentials)


async def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.is_admin:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Admin privileges required")
    return current_user


def get_ai_provider() -> AIProvider:
    """Return the configured AI provider."""
    settings = get_settings()
    provider_name = settings.ai_settings.provider

    if provider_name == "noop":
        return NoOpAIProvider()

    raise ValueError(f"Unknown AI provider: {provider_name}")

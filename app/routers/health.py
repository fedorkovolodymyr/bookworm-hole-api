from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.schemas.health_schemas import StatusResponse, VersionResponse
from app.services.health_service import HealthService

health_router = APIRouter(prefix="/health", tags=["health"])


@health_router.get("/")
async def health_check(session: AsyncSession = Depends(get_session)):
    service = HealthService()
    health_status = await service.check_overall(session)
    return health_status


@health_router.get("/live", response_model=StatusResponse)
async def health_live() -> StatusResponse:
    """Liveness probe. Always returns ok regardless of dependencies."""
    service = HealthService()
    result = await service.check_live()
    return StatusResponse(**result)


@health_router.get("/ready", response_model=StatusResponse)
async def health_ready(session: AsyncSession = Depends(get_session)) -> StatusResponse:
    """Readiness probe. Returns ok only when database is reachable."""
    service = HealthService()
    await service.check_ready(session)
    return StatusResponse(status="ok")


@health_router.get("/version", response_model=VersionResponse)
async def health_version() -> VersionResponse:
    """Returns the application version."""
    service = HealthService()
    return VersionResponse(version=service.get_version())

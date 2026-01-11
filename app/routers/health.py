from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.services.health_service import HealthService

health_router = APIRouter(prefix="/health", tags=["health"])


@health_router.get("/")
async def health_check(session: AsyncSession = Depends(get_session)):
    service = HealthService()
    health_status = await service.check_overall(session)
    return health_status

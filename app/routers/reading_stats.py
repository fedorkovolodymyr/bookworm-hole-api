from datetime import datetime

from fastapi import APIRouter, Depends, Query

from app.core.deps import get_current_user, get_reading_stats_service
from app.models.user import User
from app.schemas.reading_stats_schemas import (
    Period,
    ReadingStatsResponse,
    StreakResponse,
    TimelineResponse,
)
from app.services.reading_stats_service import ReadingStatsService

reading_stats_router = APIRouter(prefix="/me/reading", tags=["reading"])


@reading_stats_router.get("/stats", response_model=ReadingStatsResponse)
async def get_stats(
    period: Period = Query(Period.month),
    current_user: User = Depends(get_current_user),
    service: ReadingStatsService = Depends(get_reading_stats_service),
) -> ReadingStatsResponse:
    """Get reading statistics for the specified period."""
    return await service.get_stats(current_user.id, period)


@reading_stats_router.get("/streak", response_model=StreakResponse)
async def get_streak(
    current_user: User = Depends(get_current_user),
    service: ReadingStatsService = Depends(get_reading_stats_service),
) -> StreakResponse:
    """Get current and longest reading streaks."""
    return await service.get_streak(current_user.id)


@reading_stats_router.get("/timeline", response_model=TimelineResponse)
async def get_timeline(
    from_date: datetime = Query(...),
    to_date: datetime = Query(...),
    current_user: User = Depends(get_current_user),
    service: ReadingStatsService = Depends(get_reading_stats_service),
) -> TimelineResponse:
    """Get daily reading aggregates for the specified date range."""
    return await service.get_timeline(current_user.id, from_date, to_date)

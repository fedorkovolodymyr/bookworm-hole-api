from datetime import datetime
from uuid import UUID

from app.core.errors import BadRequestError, ErrorMessages
from app.repositories.reading_stats_repository import ReadingStatsRepository
from app.schemas.reading_stats_schemas import (
    Period,
    ReadingStatsResponse,
    StreakResponse,
    TimelineEntry,
    TimelineResponse,
)


class ReadingStatsService:
    def __init__(self, repository: ReadingStatsRepository) -> None:
        self.repository = repository

    async def get_stats(self, user_id: UUID, period: Period) -> ReadingStatsResponse:
        """Get reading stats for the specified period."""
        stats = await self.repository.get_stats(user_id, period)
        return ReadingStatsResponse(**stats)

    async def get_streak(self, user_id: UUID) -> StreakResponse:
        """Get current and longest reading streaks."""
        streak = await self.repository.get_streak(user_id)
        return StreakResponse(**streak)

    async def get_timeline(
        self, user_id: UUID, from_date: datetime, to_date: datetime
    ) -> TimelineResponse:
        """Get daily reading aggregates for the date range."""
        if from_date > to_date:
            raise BadRequestError(ErrorMessages.INVALID_DATE_RANGE)

        timeline_data = await self.repository.get_timeline(user_id, from_date, to_date)
        items = [
            TimelineEntry(
                date=str(item["date"]),
                total_minutes=int(item["total_minutes"]),
                sessions=int(item["sessions"]),
                pages_read=int(item["pages_read"]),
            )
            for item in timeline_data
        ]
        return TimelineResponse(items=items)

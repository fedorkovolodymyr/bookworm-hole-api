from datetime import datetime
from uuid import UUID

from sqlalchemy import func, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col, select

from app.models.reading_session import ReadingSession
from app.schemas.reading_stats_schemas import Period


class ReadingStatsRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_stats(self, user_id: UUID, period: Period) -> dict[str, int]:
        """Get aggregate reading stats for the given period."""

        interval_map = {
            Period.week: "7 days",
            Period.month: "30 days",
            Period.year: "365 days",
            Period.all: None,
        }
        interval_str = interval_map[period]

        query = select(
            func.coalesce(
                func.sum(
                    func.extract(
                        "epoch",
                        col(ReadingSession.ended_at) - col(ReadingSession.started_at),
                    )
                )
                / 60,
                0,
            ).label("total_minutes"),
            func.count(col(ReadingSession.id)).label("total_sessions"),
            func.count(func.distinct(col(ReadingSession.release_id))).label(
                "unique_books"
            ),
            func.coalesce(func.sum(col(ReadingSession.pages_read)), 0).label(
                "total_pages"
            ),
        ).where(
            col(ReadingSession.user_id) == user_id,
            col(ReadingSession.ended_at).isnot(None),
        )

        if interval_str:
            query = query.where(
                col(ReadingSession.ended_at)
                >= text(f"NOW() AT TIME ZONE 'UTC' - INTERVAL '{interval_str}'")
            )

        result = await self.session.execute(query)
        row = result.one()

        return {
            "total_minutes": int(row.total_minutes or 0),
            "total_sessions": int(row.total_sessions or 0),
            "unique_books": int(row.unique_books or 0),
            "total_pages": int(row.total_pages or 0),
        }

    async def get_streak(self, user_id: UUID) -> dict[str, int]:
        """
        Calculate current and longest reading streaks.
        Streak = consecutive days with at least one session ending.
        """
        query_str = """
        WITH daily_sessions AS (
            SELECT DISTINCT DATE(rs.ended_at AT TIME ZONE 'UTC') as session_date
            FROM reading_sessions rs
            WHERE rs.user_id = :user_id AND rs.ended_at IS NOT NULL
            ORDER BY session_date DESC
        ),
        gaps AS (
            SELECT
                session_date,
                LAG(session_date) OVER (ORDER BY session_date DESC) as prev_date,
                (LAG(session_date) OVER (ORDER BY session_date DESC)::date
                 - session_date::date) as gap_days
            FROM daily_sessions
        ),
        streaks AS (
            SELECT
                SUM(CASE WHEN gap_days != 1 THEN 1 ELSE 0 END) OVER (
                    ORDER BY session_date DESC
                ) as streak_group,
                session_date
            FROM gaps
        ),
        streak_lengths AS (
            SELECT
                streak_group,
                COUNT(*) as length,
                MAX(session_date) as max_date
            FROM streaks
            GROUP BY streak_group
        )
        SELECT
            (MAX(CASE WHEN max_date::date = (NOW() AT TIME ZONE 'UTC')::date
            THEN length ELSE 0 END) OVER ())::int as current_streak_days,
            MAX(length) as longest_streak_days
        FROM streak_lengths
        """

        result = await self.session.execute(
            text(query_str),
            {"user_id": str(user_id)},
        )
        row = result.first()

        if row is None:
            return {"current_streak_days": 0, "longest_streak_days": 0}

        current = row.current_streak_days or 0
        longest = row.longest_streak_days or 0

        return {
            "current_streak_days": int(current),
            "longest_streak_days": int(longest),
        }

    async def get_timeline(
        self, user_id: UUID, from_date: datetime, to_date: datetime
    ) -> list[dict[str, str | int]]:
        """
        Get daily aggregates for the date range [from_date, to_date].
        Uses generate_series to fill gaps (zero-session days).
        """
        query_str = """
        SELECT
            day::date as date,
            COALESCE(
                SUM(EXTRACT(EPOCH FROM (rs.ended_at - rs.started_at))) / 60,
                0
            )::int as total_minutes,
            COALESCE(COUNT(rs.id), 0)::int as sessions,
            COALESCE(SUM(rs.pages_read), 0)::int as pages_read
        FROM generate_series(
            :from_date::date,
            :to_date::date,
            INTERVAL '1 day'
        ) as day
        LEFT JOIN reading_sessions rs ON
            DATE(rs.ended_at AT TIME ZONE 'UTC') = day::date
            AND rs.user_id = :user_id
            AND rs.ended_at IS NOT NULL
        GROUP BY day
        ORDER BY day ASC
        """

        result = await self.session.execute(
            text(query_str),
            {
                "from_date": from_date.date(),
                "to_date": to_date.date(),
                "user_id": str(user_id),
            },
        )
        rows = result.fetchall()

        return [
            {
                "date": str(row.date),
                "total_minutes": int(row.total_minutes),
                "sessions": int(row.sessions),
                "pages_read": int(row.pages_read),
            }
            for row in rows
        ]

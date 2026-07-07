from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class Period(str, Enum):
    week = "week"
    month = "month"
    year = "year"
    all = "all"


class ReadingStatsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    total_minutes: int
    total_sessions: int
    unique_books: int
    total_pages: int


class StreakResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    current_streak_days: int
    longest_streak_days: int


class TimelineEntry(BaseModel):
    date: str = Field(description="ISO date (YYYY-MM-DD)")
    total_minutes: int
    sessions: int
    pages_read: int


class TimelineResponse(BaseModel):
    items: list[TimelineEntry]

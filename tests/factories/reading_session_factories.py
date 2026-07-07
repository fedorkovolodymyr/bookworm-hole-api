"""ReadingSession factory for generating test reading session instances."""

from datetime import UTC, datetime

from polyfactory.factories.sqlalchemy_factory import SQLAlchemyFactory

from app.models.reading_session import ReadingSession


class ReadingSessionFactory(SQLAlchemyFactory[ReadingSession]):
    """Factory for generating ReadingSession instances."""

    __model__ = ReadingSession

    @staticmethod
    def __started_at__() -> datetime:
        """Generate session start timestamp."""
        return datetime.now(UTC)

    class Config:
        """Polyfactory configuration."""

        create_foreign_key_relations = False

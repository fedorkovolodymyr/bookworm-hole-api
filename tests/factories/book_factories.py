"""Book, Release, and ISBN factories for generating test instances."""

from datetime import UTC, datetime

from polyfactory.factories.sqlalchemy_factory import SQLAlchemyFactory

from app.models.catalog import ISBN, Book, Release


class BookFactory(SQLAlchemyFactory[Book]):
    """Factory for generating Book instances."""

    __model__ = Book

    class Config:
        """Polyfactory configuration."""

        create_foreign_key_relations = False


class ReleaseFactory(SQLAlchemyFactory[Release]):
    """Factory for generating Release instances."""

    __model__ = Release

    @staticmethod
    def __last_external_sync_at__() -> datetime:
        """Generate a recent sync timestamp."""
        return datetime.now(UTC)

    class Config:
        """Polyfactory configuration."""

        create_foreign_key_relations = False


class ISBNFactory(SQLAlchemyFactory[ISBN]):
    """Factory for generating ISBN instances."""

    __model__ = ISBN

    @staticmethod
    def __created_at__() -> datetime:
        """Generate creation timestamp."""
        return datetime.now(UTC)

    class Config:
        """Polyfactory configuration."""

        create_foreign_key_relations = False

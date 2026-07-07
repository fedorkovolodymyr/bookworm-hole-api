"""Collection and CollectionItem factories for generating test instances."""

from datetime import UTC, datetime

from polyfactory.factories.sqlalchemy_factory import SQLAlchemyFactory

from app.models.collection import Collection, CollectionItem


class CollectionFactory(SQLAlchemyFactory[Collection]):
    """Factory for generating Collection instances."""

    __model__ = Collection

    class Config:
        """Polyfactory configuration."""

        create_foreign_key_relations = False


class CollectionItemFactory(SQLAlchemyFactory[CollectionItem]):
    """Factory for generating CollectionItem instances."""

    __model__ = CollectionItem

    @staticmethod
    def __added_at__() -> datetime:
        """Generate addition timestamp."""
        return datetime.now(UTC)

    class Config:
        """Polyfactory configuration."""

        create_foreign_key_relations = False

"""Review factory for generating test review instances."""

from polyfactory.factories.sqlalchemy_factory import SQLAlchemyFactory

from app.models.review import Review


class ReviewFactory(SQLAlchemyFactory[Review]):
    """Factory for generating Review instances."""

    __model__ = Review

    class Config:
        """Polyfactory configuration."""

        create_foreign_key_relations = False

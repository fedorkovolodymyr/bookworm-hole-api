"""Friendship factory for generating test friendship instances."""

from polyfactory.factories.sqlalchemy_factory import SQLAlchemyFactory

from app.models.friendship import Friendship


class FriendshipFactory(SQLAlchemyFactory[Friendship]):
    """Factory for generating Friendship instances."""

    __model__ = Friendship

    class Config:
        """Polyfactory configuration."""

        create_foreign_key_relations = False

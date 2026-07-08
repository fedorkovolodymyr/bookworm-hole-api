"""Contributor factory for generating test contributor instances."""

from polyfactory.factories.sqlalchemy_factory import SQLAlchemyFactory

from app.models.catalog import Contributor


class ContributorFactory(SQLAlchemyFactory[Contributor]):
    """Factory for generating Contributor instances."""

    __model__ = Contributor

    class Config:
        """Polyfactory configuration."""

        create_foreign_key_relations = False

"""User factory for generating test user instances."""

from polyfactory.factories.sqlalchemy_factory import SQLAlchemyFactory

from app.models.user import User
from app.services.security import hash_password


class UserFactory(SQLAlchemyFactory[User]):
    """Factory for generating User instances."""

    __model__ = User

    @staticmethod
    def __password_hash__() -> str:
        """Generate a hashed password for testing."""
        return hash_password("test-password-123")

    class Config:
        """Polyfactory configuration."""

        create_foreign_key_relations = False

from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.repositories.user_repository import UserRepository


class TestMarkEmailVerified:
    async def test_sets_email_verified_at(self, db_session: AsyncSession):
        user = User(email="reader@example.com", username="reader", display_name="R")
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        repository = UserRepository(db_session)

        result = await repository.mark_email_verified(user.id)

        assert result is not None
        assert result.email_verified_at is not None

    async def test_returns_none_for_unknown_user(self, db_session: AsyncSession):
        repository = UserRepository(db_session)

        result = await repository.mark_email_verified(uuid4())

        assert result is None

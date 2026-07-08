from collections.abc import Sequence
from datetime import datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col, select

from app.models.user import User
from app.schemas.user_schemas import UpdateUserSchema


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, user: User) -> User:
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def get_by_id(self, user_id: UUID) -> User | None:
        return await self.session.get(User, user_id)

    async def get_by_email(self, email: str) -> User | None:
        result = await self.session.execute(
            select(User).where(col(User.email) == email)
        )
        return result.scalars().first()

    async def get_by_username(self, username: str) -> User | None:
        result = await self.session.execute(
            select(User).where(col(User.username) == username)
        )
        return result.scalars().first()

    async def update(self, user_id: UUID, data: UpdateUserSchema) -> User | None:
        user = await self.session.get(User, user_id)
        if not user:
            return None
        user.sqlmodel_update(data.model_dump(exclude_unset=True))
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def update_password(self, user_id: UUID, password_hash: str) -> User | None:
        user = await self.session.get(User, user_id)
        if not user:
            return None
        user.password_hash = password_hash
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def deactivate(self, user_id: UUID) -> User | None:
        user = await self.session.get(User, user_id)
        if not user:
            return None
        user.is_active = False
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def schedule_deletion(
        self, user_id: UUID, scheduled_at: datetime
    ) -> User | None:
        user = await self.session.get(User, user_id)
        if not user:
            return None
        user.deletion_scheduled_at = scheduled_at
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def cancel_deletion(self, user_id: UUID) -> User | None:
        user = await self.session.get(User, user_id)
        if not user:
            return None
        user.deletion_scheduled_at = None
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def get_users_pending_purge(self, cutoff: datetime) -> Sequence[User]:
        result = await self.session.execute(
            select(User).where(col(User.deletion_scheduled_at) <= cutoff)
        )
        return result.scalars().all()

from collections.abc import Sequence
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import ColumnElement, func
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

    async def mark_email_verified(self, user_id: UUID) -> User | None:
        user = await self.session.get(User, user_id)
        if not user:
            return None
        user.email_verified_at = datetime.now(UTC)
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

    async def activate(self, user_id: UUID) -> User | None:
        user = await self.session.get(User, user_id)
        if not user:
            return None
        user.is_active = True
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

    async def promote(self, user_id: UUID) -> User | None:
        user = await self.session.get(User, user_id)
        if not user:
            return None
        user.is_admin = True
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def demote(self, user_id: UUID) -> User | None:
        user = await self.session.get(User, user_id)
        if not user:
            return None
        user.is_admin = False
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def get_all(
        self,
        skip: int = 0,
        limit: int = 10,
        email: str | None = None,
        username: str | None = None,
        is_active: bool | None = None,
        is_admin: bool | None = None,
    ) -> tuple[Sequence[User], int]:
        filters: list[ColumnElement[bool]] = []

        if email:
            filters.append(col(User.email).ilike(f"%{email}%"))
        if username:
            filters.append(col(User.username).ilike(f"%{username}%"))
        if is_active is not None:
            filters.append(col(User.is_active) == is_active)
        if is_admin is not None:
            filters.append(col(User.is_admin) == is_admin)

        base_query = select(User).order_by(col(User.created_at).desc())
        count_query = select(func.count(col(User.id)))

        for condition in filters:
            base_query = base_query.where(condition)
            count_query = count_query.where(condition)

        total = (await self.session.execute(count_query)).scalar() or 0

        result = await self.session.execute(base_query.offset(skip).limit(limit))
        users = result.scalars().all()
        return users, total

    async def get_users_pending_purge(self, cutoff: datetime) -> Sequence[User]:
        result = await self.session.execute(
            select(User).where(col(User.deletion_scheduled_at) <= cutoff)
        )
        return result.scalars().all()

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import and_, case, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col, select

from app.models.friendship import Friendship, FriendshipStatus
from app.models.user import User


class FriendshipRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def save(self, friendship: Friendship) -> Friendship:
        self.session.add(friendship)
        await self.session.commit()
        await self.session.refresh(friendship)
        return friendship

    async def get_by_id(self, friendship_id: UUID) -> Friendship | None:
        return await self.session.get(Friendship, friendship_id, populate_existing=True)

    async def get_between(self, user_a: UUID, user_b: UUID) -> Friendship | None:
        result = await self.session.execute(
            select(Friendship).where(
                or_(
                    and_(
                        col(Friendship.requester_id) == user_a,
                        col(Friendship.addressee_id) == user_b,
                    ),
                    and_(
                        col(Friendship.requester_id) == user_b,
                        col(Friendship.addressee_id) == user_a,
                    ),
                )
            )
        )
        return result.scalars().first()

    async def list_incoming_pending(self, user_id: UUID) -> Sequence[Friendship]:
        result = await self.session.execute(
            select(Friendship).where(
                col(Friendship.addressee_id) == user_id,
                col(Friendship.status) == FriendshipStatus.pending,
            )
        )
        return result.scalars().all()

    async def list_outgoing_pending(self, user_id: UUID) -> Sequence[Friendship]:
        result = await self.session.execute(
            select(Friendship).where(
                col(Friendship.requester_id) == user_id,
                col(Friendship.status) == FriendshipStatus.pending,
            )
        )
        return result.scalars().all()

    async def list_friends(self, user_id: UUID) -> Sequence[tuple[Friendship, User]]:
        other_user_id = case(
            (col(Friendship.requester_id) == user_id, Friendship.addressee_id),
            else_=Friendship.requester_id,
        )
        result = await self.session.execute(
            select(Friendship, User)
            .join(User, col(User.id) == other_user_id)
            .where(
                or_(
                    col(Friendship.requester_id) == user_id,
                    col(Friendship.addressee_id) == user_id,
                ),
                col(Friendship.status) == FriendshipStatus.accepted,
            )
        )
        return [(friendship, user) for friendship, user in result.all()]

    async def delete(self, friendship_id: UUID) -> bool:
        friendship = await self.session.get(Friendship, friendship_id)
        if not friendship:
            return False
        await self.session.delete(friendship)
        await self.session.commit()
        return True

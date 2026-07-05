from collections.abc import Sequence
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.exc import IntegrityError

from app.core.errors import (
    BadRequestError,
    ConflictError,
    ErrorMessages,
    NotFoundError,
)
from app.models.friendship import Friendship, FriendshipStatus
from app.repositories.friendship_repository import FriendshipRepository
from app.repositories.user_repository import UserRepository
from app.schemas.friendship_schemas import FriendResponse, SendFriendRequestSchema


class FriendshipService:
    def __init__(
        self, repository: FriendshipRepository, user_repository: UserRepository
    ):
        self.repository = repository
        self.user_repository = user_repository

    async def _get_pending_as_addressee(
        self, user_id: UUID, friendship_id: UUID
    ) -> Friendship:
        friendship = await self.repository.get_by_id(friendship_id)
        if (
            not friendship
            or friendship.addressee_id != user_id
            or friendship.status != FriendshipStatus.pending
        ):
            raise NotFoundError(ErrorMessages.FRIEND_REQUEST_NOT_FOUND)
        return friendship

    async def send_request(
        self, user_id: UUID, data: SendFriendRequestSchema
    ) -> Friendship:
        target = await self.user_repository.get_by_username(data.username)
        if not target:
            raise NotFoundError(ErrorMessages.USER_NOT_FOUND)
        if target.id == user_id:
            raise BadRequestError(ErrorMessages.SELF_FRIEND_REQUEST_NOT_ALLOWED)

        existing = await self.repository.get_between(user_id, target.id)
        if existing is None:
            friendship = Friendship(
                requester_id=user_id,
                addressee_id=target.id,
                status=FriendshipStatus.pending,
            )
            try:
                return await self.repository.save(friendship)
            except IntegrityError as exc:
                raise ConflictError(
                    ErrorMessages.FRIEND_REQUEST_ALREADY_EXISTS
                ) from exc

        if existing.status == FriendshipStatus.blocked:
            raise ConflictError(ErrorMessages.USER_BLOCKED)
        if existing.status == FriendshipStatus.accepted:
            raise ConflictError(ErrorMessages.ALREADY_FRIENDS)
        if existing.status == FriendshipStatus.pending:
            if existing.requester_id == user_id:
                raise ConflictError(ErrorMessages.FRIEND_REQUEST_ALREADY_EXISTS)
            existing.status = FriendshipStatus.accepted
            existing.responded_at = datetime.now(UTC)
            return await self.repository.save(existing)

        existing.requester_id = user_id
        existing.addressee_id = target.id
        existing.status = FriendshipStatus.pending
        existing.responded_at = None
        return await self.repository.save(existing)

    async def list_incoming(self, user_id: UUID) -> Sequence[Friendship]:
        return await self.repository.list_incoming_pending(user_id)

    async def list_outgoing(self, user_id: UUID) -> Sequence[Friendship]:
        return await self.repository.list_outgoing_pending(user_id)

    async def accept(self, user_id: UUID, friendship_id: UUID) -> Friendship:
        friendship = await self._get_pending_as_addressee(user_id, friendship_id)
        friendship.status = FriendshipStatus.accepted
        friendship.responded_at = datetime.now(UTC)
        return await self.repository.save(friendship)

    async def decline(self, user_id: UUID, friendship_id: UUID) -> Friendship:
        friendship = await self._get_pending_as_addressee(user_id, friendship_id)
        friendship.status = FriendshipStatus.declined
        friendship.responded_at = datetime.now(UTC)
        return await self.repository.save(friendship)

    async def list_friends(self, user_id: UUID) -> list[FriendResponse]:
        pairs = await self.repository.list_friends(user_id)
        return [
            FriendResponse(
                user_id=other.id,
                username=other.username,
                display_name=other.display_name,
                avatar_url=other.avatar_url,
                since=friendship.responded_at or friendship.created_at,
            )
            for friendship, other in pairs
        ]

    async def unfriend(self, user_id: UUID, target_user_id: UUID) -> None:
        friendship = await self.repository.get_between(user_id, target_user_id)
        if not friendship or friendship.status != FriendshipStatus.accepted:
            raise NotFoundError(ErrorMessages.FRIENDSHIP_NOT_FOUND)
        await self.repository.delete(friendship.id)

    async def block(self, user_id: UUID, target_user_id: UUID) -> Friendship:
        if target_user_id == user_id:
            raise BadRequestError(ErrorMessages.CANNOT_BLOCK_SELF)
        target = await self.user_repository.get_by_id(target_user_id)
        if not target:
            raise NotFoundError(ErrorMessages.USER_NOT_FOUND)

        existing = await self.repository.get_between(user_id, target_user_id)
        if existing is None:
            friendship = Friendship(
                requester_id=user_id,
                addressee_id=target_user_id,
                status=FriendshipStatus.blocked,
                responded_at=datetime.now(UTC),
            )
            return await self.repository.save(friendship)

        existing.requester_id = user_id
        existing.addressee_id = target_user_id
        existing.status = FriendshipStatus.blocked
        existing.responded_at = datetime.now(UTC)
        return await self.repository.save(existing)

    async def unblock(self, user_id: UUID, target_user_id: UUID) -> None:
        friendship = await self.repository.get_between(user_id, target_user_id)
        if (
            not friendship
            or friendship.status != FriendshipStatus.blocked
            or friendship.requester_id != user_id
        ):
            raise NotFoundError(ErrorMessages.FRIENDSHIP_NOT_FOUND)
        await self.repository.delete(friendship.id)

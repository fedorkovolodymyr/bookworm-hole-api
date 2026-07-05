from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.deps import get_current_user
from app.models.user import User
from app.repositories.friendship_repository import FriendshipRepository
from app.repositories.user_repository import UserRepository
from app.schemas.friendship_schemas import (
    FriendRequestResponse,
    FriendResponse,
    SendFriendRequestSchema,
)
from app.services.friendship_service import FriendshipService

friends_router = APIRouter(prefix="/friends", tags=["friends"])


def get_friendship_service(
    session: AsyncSession = Depends(get_session),
) -> FriendshipService:
    return FriendshipService(FriendshipRepository(session), UserRepository(session))


@friends_router.post(
    "/requests",
    response_model=FriendRequestResponse,
    status_code=status.HTTP_201_CREATED,
)
async def send_friend_request(
    data: SendFriendRequestSchema,
    current_user: User = Depends(get_current_user),
    service: FriendshipService = Depends(get_friendship_service),
):
    return await service.send_request(current_user.id, data)


@friends_router.get("/requests/incoming", response_model=list[FriendRequestResponse])
async def list_incoming_requests(
    current_user: User = Depends(get_current_user),
    service: FriendshipService = Depends(get_friendship_service),
):
    return await service.list_incoming(current_user.id)


@friends_router.get("/requests/outgoing", response_model=list[FriendRequestResponse])
async def list_outgoing_requests(
    current_user: User = Depends(get_current_user),
    service: FriendshipService = Depends(get_friendship_service),
):
    return await service.list_outgoing(current_user.id)


@friends_router.post(
    "/requests/{friendship_id}/accept", response_model=FriendRequestResponse
)
async def accept_friend_request(
    friendship_id: UUID,
    current_user: User = Depends(get_current_user),
    service: FriendshipService = Depends(get_friendship_service),
):
    return await service.accept(current_user.id, friendship_id)


@friends_router.post(
    "/requests/{friendship_id}/decline", response_model=FriendRequestResponse
)
async def decline_friend_request(
    friendship_id: UUID,
    current_user: User = Depends(get_current_user),
    service: FriendshipService = Depends(get_friendship_service),
):
    return await service.decline(current_user.id, friendship_id)


@friends_router.get("/", response_model=list[FriendResponse])
async def list_friends(
    current_user: User = Depends(get_current_user),
    service: FriendshipService = Depends(get_friendship_service),
):
    return await service.list_friends(current_user.id)


@friends_router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_friend(
    user_id: UUID,
    current_user: User = Depends(get_current_user),
    service: FriendshipService = Depends(get_friendship_service),
) -> None:
    await service.unfriend(current_user.id, user_id)


@friends_router.post(
    "/{user_id}/block",
    response_model=FriendRequestResponse,
    status_code=status.HTTP_201_CREATED,
)
async def block_user(
    user_id: UUID,
    current_user: User = Depends(get_current_user),
    service: FriendshipService = Depends(get_friendship_service),
):
    return await service.block(current_user.id, user_id)


@friends_router.delete("/{user_id}/block", status_code=status.HTTP_204_NO_CONTENT)
async def unblock_user(
    user_id: UUID,
    current_user: User = Depends(get_current_user),
    service: FriendshipService = Depends(get_friendship_service),
) -> None:
    await service.unblock(current_user.id, user_id)

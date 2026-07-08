from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.deps import get_current_user
from app.core.errors import NotFoundError
from app.models.user import User
from app.repositories.chat_repository import ChatRepository
from app.repositories.friendship_repository import FriendshipRepository
from app.schemas.chat_schemas import (
    ChatMessageResponse,
    ChatThreadWithLastMessageResponse,
    SendChatMessageSchema,
)
from app.services.chat_service import ChatService

chat_router = APIRouter(prefix="/chat", tags=["chat"])


def get_chat_service(
    session: AsyncSession = Depends(get_session),
) -> ChatService:
    return ChatService(ChatRepository(session), FriendshipRepository(session))


@chat_router.get("/threads/", response_model=list[ChatThreadWithLastMessageResponse])
async def list_chat_threads(
    current_user: User = Depends(get_current_user),
    service: ChatService = Depends(get_chat_service),
) -> list[ChatThreadWithLastMessageResponse]:
    """List all chat threads for the current user, with last message preview."""
    threads = await service.list_threads(current_user.id)
    result: list[ChatThreadWithLastMessageResponse] = []
    for thread in threads:
        last_message = await service.chat_repo.get_last_message_for_thread(thread.id)
        last_msg_response: ChatMessageResponse | None = None
        if last_message:
            last_msg_response = ChatMessageResponse.model_validate(last_message)
        result.append(
            ChatThreadWithLastMessageResponse(
                id=thread.id,
                user_a_id=thread.user_a_id,
                user_b_id=thread.user_b_id,
                last_message_at=thread.last_message_at,
                created_at=thread.created_at,
                last_message=last_msg_response,
            )
        )
    return result


@chat_router.get(
    "/threads/{thread_id}/messages", response_model=list[ChatMessageResponse]
)
async def get_thread_messages(
    thread_id: UUID,
    before: UUID | None = Query(None),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    service: ChatService = Depends(get_chat_service),
):
    """Get paginated message history using cursor-based pagination."""
    return await service.get_messages(thread_id, current_user.id, before, limit)


@chat_router.post("/threads/{thread_id}/messages", response_model=ChatMessageResponse)
async def send_message_to_thread(
    thread_id: UUID,
    data: SendChatMessageSchema,
    current_user: User = Depends(get_current_user),
    service: ChatService = Depends(get_chat_service),
):
    """Send a message to an existing thread."""
    thread = await service.chat_repo.get_thread_by_id(thread_id)
    if not thread:
        raise NotFoundError("Chat thread not found")

    # Determine recipient from thread
    if thread.user_a_id == current_user.id:
        recipient_id = thread.user_b_id
    elif thread.user_b_id == current_user.id:
        recipient_id = thread.user_a_id
    else:
        raise NotFoundError("Chat thread not found")

    return await service.send_message(current_user.id, recipient_id, data)


@chat_router.post("/threads/{thread_id}/read", status_code=status.HTTP_204_NO_CONTENT)
async def mark_thread_read(
    thread_id: UUID,
    current_user: User = Depends(get_current_user),
    service: ChatService = Depends(get_chat_service),
) -> None:
    """Mark all messages in a thread as read for the current user."""
    await service.mark_thread_read(thread_id, current_user.id)

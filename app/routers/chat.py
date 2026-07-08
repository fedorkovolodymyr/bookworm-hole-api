import asyncio
import json
from typing import Any
from uuid import UUID

import jwt
from fastapi import (
    APIRouter,
    Depends,
    Query,
    Request,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import async_session_factory, get_session
from app.core.deps import get_current_user
from app.core.security import decode_token
from app.models.user import User
from app.repositories.chat_repository import ChatRepository
from app.repositories.friendship_repository import FriendshipRepository
from app.routers.responses import NOT_FOUND_RESPONSE
from app.schemas.chat_schemas import (
    ChatMessageResponse,
    ChatThreadResponse,
    ChatThreadWithLastMessageResponse,
    SendChatMessageSchema,
    StartChatThreadSchema,
)
from app.services.chat_service import ChatService
from app.services.websocket_manager import WebSocketConnectionManager

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


@chat_router.post("/threads", response_model=ChatThreadResponse)
async def start_chat_thread(
    data: StartChatThreadSchema,
    current_user: User = Depends(get_current_user),
    service: ChatService = Depends(get_chat_service),
):
    """Get or create the thread with a friend, auto-creating it on first contact."""
    return await service.get_or_create_thread(current_user.id, data.recipient_id)


@chat_router.get(
    "/threads/{thread_id}/messages",
    response_model=list[ChatMessageResponse],
    responses=NOT_FOUND_RESPONSE,
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


@chat_router.post(
    "/threads/{thread_id}/messages",
    response_model=ChatMessageResponse,
    responses=NOT_FOUND_RESPONSE,
)
async def send_message_to_thread(
    thread_id: UUID,
    data: SendChatMessageSchema,
    request: Request,
    current_user: User = Depends(get_current_user),
    service: ChatService = Depends(get_chat_service),
):
    """Send a message to an existing thread."""
    message = await service.send_message_to_thread(thread_id, current_user.id, data)
    manager: WebSocketConnectionManager = request.app.state.websocket_manager
    await manager.broadcast(
        thread_id, ChatMessageResponse.model_validate(message).model_dump(mode="json")
    )
    return message


@chat_router.post(
    "/threads/{thread_id}/read",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=NOT_FOUND_RESPONSE,
)
async def mark_thread_read(
    thread_id: UUID,
    current_user: User = Depends(get_current_user),
    service: ChatService = Depends(get_chat_service),
) -> None:
    """Mark all messages in a thread as read for the current user."""
    await service.mark_thread_read(thread_id, current_user.id)


async def _authenticate_from_query(token: str) -> UUID | None:
    try:
        payload = decode_token(token)
        return UUID(payload.get("sub", ""))
    except (jwt.PyJWTError, ValueError) as e:
        logger.debug(f"Token auth failed: {e}")
        return None


async def _authenticate_from_message(
    message: dict[str, Any],
) -> UUID | None:
    try:
        token = message.get("token", "")
        payload = decode_token(token)
        return UUID(payload.get("sub", ""))
    except (jwt.PyJWTError, ValueError) as e:
        logger.debug(f"First-message auth failed: {e}")
        return None


async def _authenticate(websocket: WebSocket, token: str | None) -> UUID | None:
    """Authenticate via query param token, or via a first `authenticate` message."""
    if token:
        return await _authenticate_from_query(token)

    try:
        data = await asyncio.wait_for(websocket.receive_text(), timeout=10.0)
        message = json.loads(data)
    except (TimeoutError, json.JSONDecodeError):
        return None

    if message.get("type") != "authenticate":
        return None
    return await _authenticate_from_message(message)


@chat_router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    thread_id: UUID = Query(..., description="Chat thread ID"),
    token: str | None = Query(
        None,
        description="JWT token for authentication (alternative to first message auth)",
    ),
) -> None:
    """WebSocket endpoint for real-time chat messaging.

    Supports two authentication methods:
    1. Query param: `?thread_id=<uuid>&token=<jwt>`
    2. First message: `{"type": "authenticate", "token": "<jwt>"}`

    Broadcasts messages sent via `POST /chat/threads/{thread_id}/messages` to
    both participants. Sends a heartbeat ping every 30 seconds.
    """
    manager: WebSocketConnectionManager = websocket.app.state.websocket_manager
    heartbeat_task: asyncio.Task[Any] | None = None

    await websocket.accept()
    user_id = await _authenticate(websocket, token)
    if user_id is None:
        await websocket.close(code=1008, reason="Unauthorized: invalid token")
        return

    async with async_session_factory() as session:
        chat_repo = ChatRepository(session)
        thread = await chat_repo.get_thread_by_id(thread_id)
        if not thread or user_id not in (thread.user_a_id, thread.user_b_id):
            await websocket.close(code=1008, reason="Unauthorized: not a participant")
            return

    try:
        await manager.connect(websocket, thread_id, user_id)
        heartbeat_task = asyncio.create_task(
            manager.heartbeat_loop(websocket, interval=30)
        )

        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            if message.get("type") == "heartbeat":
                await manager.send_heartbeat(websocket)

    except WebSocketDisconnect:
        logger.debug(f"WebSocket disconnected: thread_id={thread_id}")
    except json.JSONDecodeError:
        logger.debug("Invalid JSON received on WebSocket")
    finally:
        await manager.disconnect(websocket)
        if heartbeat_task:
            heartbeat_task.cancel()

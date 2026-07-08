"""Chat router: REST endpoints and WebSocket for real-time messaging."""

import asyncio
import json
from typing import Any
from uuid import UUID

import jwt
from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from loguru import logger

from app.core.security import decode_token
from app.schemas.websocket_schemas import (
    WebSocketAuthMessage,
    WebSocketChatMessage,
)
from app.services.websocket_manager import WebSocketConnectionManager

chat_router = APIRouter(prefix="/chat", tags=["chat"])


async def _authenticate_from_query(token: str, thread_id: UUID) -> tuple[UUID, bool]:
    """Authenticate from query param token.

    Returns: (user_id, success)
    """
    try:
        payload = decode_token(token)
        user_id = UUID(payload.get("sub", ""))
        return user_id, True
    except (jwt.PyJWTError, ValueError) as e:
        logger.debug(f"Token auth failed: {e}")
        return UUID(int=0), False


async def _authenticate_from_message(
    message: dict[str, Any], thread_id: UUID
) -> tuple[UUID, bool]:
    """Authenticate from first message.

    Returns: (user_id, success)
    """
    try:
        auth_msg = WebSocketAuthMessage(**message)
        if auth_msg.thread_id != thread_id:
            logger.debug("thread_id mismatch in first message auth")
            return UUID(int=0), False

        payload = decode_token(auth_msg.token)
        user_id = UUID(payload.get("sub", ""))
        return user_id, True
    except (jwt.PyJWTError, ValueError) as e:
        logger.debug(f"First-message auth failed: {e}")
        return UUID(int=0), False


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
    2. First message: `{"type": "authenticate", "token": "<jwt>",
       "thread_id": "<uuid>"}`

    Broadcasts messages to both participants in the thread.
    Sends heartbeat ping every 30 seconds.
    """
    manager: WebSocketConnectionManager = websocket.app.state.websocket_manager
    user_id: UUID | None = None
    heartbeat_task: asyncio.Task[Any] | None = None

    try:
        if token:
            user_id, success = await _authenticate_from_query(token, thread_id)
            if not success:
                await websocket.close(code=1008, reason="Unauthorized: invalid token")
                return
        else:
            await websocket.accept()
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=10.0)
                message = json.loads(data)
                if message.get("type") == "authenticate":
                    user_id, success = await _authenticate_from_message(
                        message, thread_id
                    )
                    if not success:
                        await websocket.close(
                            code=1008, reason="Unauthorized: invalid token"
                        )
                        return
                else:
                    await websocket.close(
                        code=1008, reason="Unauthorized: authenticate first"
                    )
                    return
            except TimeoutError:
                await websocket.close(code=1008, reason="Unauthorized: auth timeout")
                return

        await manager.connect(websocket, thread_id, user_id)
        heartbeat_task = asyncio.create_task(
            manager.heartbeat_loop(websocket, interval=30)
        )

        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            msg_type = message.get("type", "")

            if msg_type == "message":
                chat_msg = WebSocketChatMessage(**message)
                await manager.broadcast(thread_id, chat_msg.data)
            elif msg_type == "heartbeat":
                await manager.send_heartbeat(websocket)

    except WebSocketDisconnect:
        logger.debug(f"WebSocket disconnected: thread_id={thread_id}")
    except json.JSONDecodeError:
        logger.debug("Invalid JSON received on WebSocket")
    except RuntimeError as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        await manager.disconnect(websocket)
        if heartbeat_task:
            heartbeat_task.cancel()

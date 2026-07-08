"""In-memory WebSocket connection manager for real-time chat broadcasting."""

import asyncio
import contextlib
import json
from typing import Any
from uuid import UUID

from fastapi import WebSocket
from loguru import logger


class WebSocketConnectionManager:
    """Manages WebSocket connections and broadcasts messages to thread participants."""

    def __init__(self) -> None:
        """Initialize connection manager."""
        # thread_id -> set of active WebSocket connections
        self.thread_connections: dict[UUID, set[WebSocket]] = {}
        # WebSocket -> {thread_id, user_id}
        self.connection_meta: dict[WebSocket, dict[str, UUID]] = {}
        self._heartbeat_tasks: set[asyncio.Task[Any]] = set()

    async def connect(
        self, websocket: WebSocket, thread_id: UUID, user_id: UUID
    ) -> None:
        """Register a new WebSocket connection for a chat thread."""
        await websocket.accept()

        if thread_id not in self.thread_connections:
            self.thread_connections[thread_id] = set()

        self.thread_connections[thread_id].add(websocket)
        self.connection_meta[websocket] = {
            "thread_id": thread_id,
            "user_id": user_id,
        }

        logger.debug(
            f"WebSocket connected: thread_id={thread_id}, user_id={user_id}, "
            f"total={len(self.thread_connections[thread_id])}"
        )

    async def disconnect(self, websocket: WebSocket) -> None:
        """Unregister a WebSocket connection."""
        if websocket not in self.connection_meta:
            return

        meta = self.connection_meta.pop(websocket)
        thread_id = meta["thread_id"]
        user_id = meta["user_id"]

        if thread_id in self.thread_connections:
            self.thread_connections[thread_id].discard(websocket)
            if not self.thread_connections[thread_id]:
                del self.thread_connections[thread_id]

        logger.debug(
            f"WebSocket disconnected: thread_id={thread_id}, user_id={user_id}"
        )

    async def broadcast(self, thread_id: UUID, message_data: dict[str, Any]) -> None:
        """Broadcast a message to all WebSocket clients in a thread.

        Args:
            thread_id: Chat thread ID
            message_data: Message dict (will be wrapped with type and data)
        """
        if thread_id not in self.thread_connections:
            return

        broadcast_msg: dict[str, Any] = {
            "type": "message",
            "data": message_data,
        }
        payload = json.dumps(broadcast_msg)

        disconnected: set[WebSocket] = set()
        for websocket in self.thread_connections[thread_id]:
            try:
                await websocket.send_text(payload)
            except RuntimeError as e:
                logger.debug(f"Failed to send to WebSocket: {e}")
                disconnected.add(websocket)

        for ws in disconnected:
            await self.disconnect(ws)

    async def send_heartbeat(self, websocket: WebSocket) -> None:
        """Send a heartbeat ping to keep connection alive."""
        try:
            await websocket.send_json({"type": "heartbeat"})
        except RuntimeError as e:
            logger.debug(f"Failed to send heartbeat: {e}")

    async def heartbeat_loop(self, websocket: WebSocket, interval: int = 30) -> None:
        """Periodically send heartbeat pings to a connection.

        Args:
            websocket: WebSocket connection
            interval: Seconds between heartbeats
        """
        try:
            while websocket in self.connection_meta:
                await asyncio.sleep(interval)
                if websocket in self.connection_meta:
                    await self.send_heartbeat(websocket)
        except asyncio.CancelledError:
            pass
        except RuntimeError as e:
            logger.debug(f"Heartbeat loop error: {e}")

    async def shutdown(self) -> None:
        """Clean up all connections and cancel heartbeat tasks."""
        for task in self._heartbeat_tasks:
            task.cancel()
        self._heartbeat_tasks.clear()

        for websockets in self.thread_connections.values():
            for ws in list(websockets):
                with contextlib.suppress(RuntimeError):
                    await ws.close()

        self.thread_connections.clear()
        self.connection_meta.clear()

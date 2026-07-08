"""WebSocket message schemas for real-time chat."""

from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class WebSocketAuthMessage(BaseModel):
    """Authenticate connection via first message."""

    type: str = Field(default="authenticate", pattern="^authenticate$")
    token: str = Field(description="JWT token for authentication")
    thread_id: UUID = Field(description="Chat thread ID")


class WebSocketChatMessage(BaseModel):
    """Incoming chat message from client."""

    type: str = Field(default="message", pattern="^message$")
    data: dict[str, Any] = Field(description="Message data (forwarded to broadcast)")


class WebSocketHeartbeat(BaseModel):
    """Heartbeat/keepalive message."""

    type: str = Field(default="heartbeat", pattern="^heartbeat$")


class ChatMessageBroadcast(BaseModel):
    """Outgoing chat message broadcast to all clients in thread."""

    type: str = Field(default="message")
    data: dict[str, Any] = Field(description="Full ChatMessageResponse from server")


WebSocketIncoming = WebSocketAuthMessage | WebSocketChatMessage | WebSocketHeartbeat

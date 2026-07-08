from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ChatThreadResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_a_id: UUID
    user_b_id: UUID
    last_message_at: datetime | None
    created_at: datetime


class StartChatThreadSchema(BaseModel):
    recipient_id: UUID


class ChatMessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    thread_id: UUID
    sender_id: UUID
    body: str
    attachment_book_id: UUID | None
    attachment_collection_id: UUID | None
    read_at: datetime | None
    created_at: datetime


class SendChatMessageSchema(BaseModel):
    body: str
    attachment_book_id: UUID | None = None
    attachment_collection_id: UUID | None = None


class ChatThreadWithLastMessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_a_id: UUID
    user_b_id: UUID
    last_message_at: datetime | None
    created_at: datetime
    last_message: ChatMessageResponse | None = None

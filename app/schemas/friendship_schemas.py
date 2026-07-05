from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.friendship import FriendshipStatus


class SendFriendRequestSchema(BaseModel):
    username: str


class FriendRequestResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    requester_id: UUID
    addressee_id: UUID
    status: FriendshipStatus
    created_at: datetime
    responded_at: datetime | None


class FriendResponse(BaseModel):
    user_id: UUID
    username: str
    display_name: str
    avatar_url: str | None
    since: datetime

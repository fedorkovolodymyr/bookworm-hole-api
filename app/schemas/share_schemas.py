from uuid import UUID

from pydantic import BaseModel


class ShareBookSchema(BaseModel):
    friend_id: UUID
    message: str


class ShareCollectionSchema(BaseModel):
    friend_id: UUID
    message: str

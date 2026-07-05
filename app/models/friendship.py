import enum
import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, Column, DateTime, UniqueConstraint
from sqlalchemy import Enum as SAEnum
from sqlmodel import Field, SQLModel

from app.models.mixins import IdMixin, TimestampMixin


class FriendshipStatus(str, enum.Enum):
    pending = "pending"
    accepted = "accepted"
    declined = "declined"
    blocked = "blocked"


class Friendship(SQLModel, IdMixin, TimestampMixin, table=True):
    __table_args__ = (
        UniqueConstraint(
            "requester_id", "addressee_id", name="uq_friendship_requester_addressee"
        ),
        CheckConstraint(
            "requester_id != addressee_id", name="ck_friendship_no_self_friend"
        ),
    )

    requester_id: uuid.UUID = Field(foreign_key="user.id", index=True)
    addressee_id: uuid.UUID = Field(foreign_key="user.id", index=True)
    status: FriendshipStatus = Field(
        sa_column=Column(SAEnum(FriendshipStatus), nullable=False)
    )
    responded_at: datetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )

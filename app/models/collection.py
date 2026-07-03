import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, Column, DateTime, ForeignKey, Uuid, func
from sqlmodel import Field, Relationship, SQLModel

from app.models.mixins import IdMixin, TimestampMixin


class Collection(SQLModel, IdMixin, TimestampMixin, table=True):
    user_id: uuid.UUID = Field(foreign_key="user.id", index=True)
    name: str = Field(max_length=255)
    description: str | None = Field(default=None)
    is_public: bool = Field(default=False)
    cover_image_url: str | None = Field(default=None, max_length=2048)
    sort_order: int = Field(default=0)

    items: list["CollectionItem"] = Relationship(back_populates="collection")


class CollectionItem(SQLModel, IdMixin, table=True):
    __tablename__ = "collection_items"
    __table_args__ = (
        CheckConstraint(
            "(book_id IS NOT NULL AND release_id IS NULL) OR "
            "(book_id IS NULL AND release_id IS NOT NULL)",
            name="ck_collection_item_exactly_one_target",
        ),
    )

    collection_id: uuid.UUID = Field(
        sa_column=Column(
            Uuid(),
            ForeignKey("collection.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )
    )
    book_id: uuid.UUID | None = Field(default=None, foreign_key="book.id", index=True)
    release_id: uuid.UUID | None = Field(
        default=None, foreign_key="releases.id", index=True
    )
    position: int = Field(default=0)
    added_at: datetime = Field(
        sa_column=Column(
            DateTime(timezone=True),
            server_default=func.now(),
            nullable=False,
        )
    )
    note: str | None = Field(default=None)

    collection: Collection = Relationship(back_populates="items")

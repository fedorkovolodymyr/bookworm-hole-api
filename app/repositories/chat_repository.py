from collections.abc import Sequence
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col, select

from app.models.chat import ChatMessage, ChatThread


class ChatRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_thread(self, thread: ChatThread) -> ChatThread:
        self.session.add(thread)
        await self.session.commit()
        await self.session.refresh(thread)
        return thread

    async def create_message(self, message: ChatMessage) -> ChatMessage:
        self.session.add(message)
        await self.session.commit()
        await self.session.refresh(message)
        return message

    async def get_thread_by_id(self, thread_id: UUID) -> ChatThread | None:
        return await self.session.get(ChatThread, thread_id, populate_existing=True)

    async def get_thread_for_users(
        self, user_a: UUID, user_b: UUID
    ) -> ChatThread | None:
        """Get thread between two users, handling user order."""
        # Canonicalize: smaller ID first
        if user_a > user_b:
            user_a, user_b = user_b, user_a

        result = await self.session.execute(
            select(ChatThread).where(
                col(ChatThread.user_a_id) == user_a,
                col(ChatThread.user_b_id) == user_b,
            )
        )
        return result.scalars().first()

    async def list_threads_for_user(self, user_id: UUID) -> Sequence[ChatThread]:
        """List all threads involving this user, ordered by last_message_at desc."""
        result = await self.session.execute(
            select(ChatThread)
            .where(
                or_(
                    col(ChatThread.user_a_id) == user_id,
                    col(ChatThread.user_b_id) == user_id,
                )
            )
            .order_by(col(ChatThread.last_message_at).desc().nullsfirst())
        )
        return result.scalars().all()

    async def get_messages_before(
        self, thread_id: UUID, before_id: UUID | None, limit: int = 50
    ) -> Sequence[ChatMessage]:
        """Get messages before a cursor, ordered by created_at descending."""
        query = select(ChatMessage).where(col(ChatMessage.thread_id) == thread_id)

        if before_id is not None:
            before_msg = await self.session.get(ChatMessage, before_id)
            if before_msg:
                query = query.where(col(ChatMessage.created_at) < before_msg.created_at)

        query = query.order_by(col(ChatMessage.created_at).desc())
        result = await self.session.execute(query.limit(limit))
        return result.scalars().all()

    async def get_last_message_for_thread(self, thread_id: UUID) -> ChatMessage | None:
        """Get the most recent message in a thread."""
        result = await self.session.execute(
            select(ChatMessage)
            .where(col(ChatMessage.thread_id) == thread_id)
            .order_by(col(ChatMessage.created_at).desc())
            .limit(1)
        )
        return result.scalars().first()

    async def mark_messages_as_read(
        self, thread_id: UUID, except_sender_id: UUID
    ) -> int:
        """Mark all unread messages in thread as read, except those from sender_id."""
        result = await self.session.execute(
            select(ChatMessage).where(
                col(ChatMessage.thread_id) == thread_id,
                col(ChatMessage.sender_id) != except_sender_id,
                col(ChatMessage.read_at).is_(None),
            )
        )
        messages = result.scalars().all()
        count = 0
        for msg in messages:
            msg.read_at = datetime.now(UTC)
            self.session.add(msg)
            count += 1

        if count > 0:
            await self.session.commit()

        return count

    async def update_thread_last_message(self, thread_id: UUID, now: datetime) -> None:
        """Update thread's last_message_at to now."""
        thread = await self.session.get(ChatThread, thread_id)
        if thread:
            thread.last_message_at = now
            self.session.add(thread)
            await self.session.commit()

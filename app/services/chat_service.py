from collections.abc import Sequence
from datetime import UTC, datetime
from uuid import UUID

from app.core.errors import (
    ErrorMessages,
    NotFoundError,
    UnauthorizedError,
)
from app.models.chat import ChatMessage, ChatThread
from app.models.friendship import FriendshipStatus
from app.repositories.chat_repository import ChatRepository
from app.repositories.friendship_repository import FriendshipRepository
from app.schemas.chat_schemas import SendChatMessageSchema


class ChatService:
    def __init__(
        self, chat_repo: ChatRepository, friendship_repo: FriendshipRepository
    ) -> None:
        self.chat_repo = chat_repo
        self.friendship_repo = friendship_repo

    async def _verify_friendship(self, user_a: UUID, user_b: UUID) -> None:
        """Verify that users are friends and not blocked."""
        if user_a == user_b:
            raise UnauthorizedError(ErrorMessages.CANNOT_MESSAGE_SELF)

        friendship = await self.friendship_repo.get_between(user_a, user_b)
        if not friendship:
            raise UnauthorizedError(ErrorMessages.NOT_FRIENDS)
        if friendship.status != FriendshipStatus.accepted:
            raise UnauthorizedError(ErrorMessages.NOT_FRIENDS)

    async def get_or_create_thread(
        self, sender_id: UUID, recipient_id: UUID
    ) -> ChatThread:
        """Get or create the thread between two friends, canonicalizing user order."""
        await self._verify_friendship(sender_id, recipient_id)

        thread = await self.chat_repo.get_thread_for_users(sender_id, recipient_id)
        if thread:
            return thread

        user_a_id = min(sender_id, recipient_id)
        user_b_id = max(sender_id, recipient_id)
        thread = ChatThread(user_a_id=user_a_id, user_b_id=user_b_id)
        return await self.chat_repo.create_thread(thread)

    async def send_message(
        self,
        sender_id: UUID,
        recipient_id: UUID,
        data: SendChatMessageSchema,
    ) -> ChatMessage:
        """Send a message between friends, auto-creating thread if needed."""
        thread = await self.get_or_create_thread(sender_id, recipient_id)

        # Create message
        now = datetime.now(UTC)
        message = ChatMessage(
            thread_id=thread.id,
            sender_id=sender_id,
            body=data.body,
            attachment_book_id=data.attachment_book_id,
            attachment_collection_id=data.attachment_collection_id,
        )
        message = await self.chat_repo.create_message(message)

        # Update thread's last_message_at
        await self.chat_repo.update_thread_last_message(thread.id, now)

        return message

    async def send_message_to_thread(
        self,
        thread_id: UUID,
        sender_id: UUID,
        data: SendChatMessageSchema,
    ) -> ChatMessage:
        """Send a message to an existing thread, deriving the recipient from it."""
        thread = await self.chat_repo.get_thread_by_id(thread_id)
        if not thread:
            raise NotFoundError(ErrorMessages.CHAT_THREAD_NOT_FOUND)

        if thread.user_a_id == sender_id:
            recipient_id = thread.user_b_id
        elif thread.user_b_id == sender_id:
            recipient_id = thread.user_a_id
        else:
            raise NotFoundError(ErrorMessages.CHAT_THREAD_NOT_FOUND)

        return await self.send_message(sender_id, recipient_id, data)

    async def list_threads(self, user_id: UUID) -> Sequence[ChatThread]:
        """List all chat threads for a user."""
        return await self.chat_repo.list_threads_for_user(user_id)

    async def get_messages(
        self,
        thread_id: UUID,
        user_id: UUID,
        before_id: UUID | None = None,
        limit: int = 50,
    ) -> Sequence[ChatMessage]:
        """Get paginated messages from a thread (caller must have access)."""
        thread = await self.chat_repo.get_thread_by_id(thread_id)
        if not thread:
            raise NotFoundError(ErrorMessages.CHAT_THREAD_NOT_FOUND)

        # Verify user has access to this thread
        if user_id != thread.user_a_id and user_id != thread.user_b_id:
            raise NotFoundError(ErrorMessages.CHAT_THREAD_NOT_FOUND)

        # Get messages and mark as read
        messages = await self.chat_repo.get_messages_before(thread_id, before_id, limit)
        await self.chat_repo.mark_messages_as_read(thread_id, user_id)

        return messages

    async def mark_thread_read(self, thread_id: UUID, user_id: UUID) -> int:
        """Mark all messages in thread as read for this user."""
        thread = await self.chat_repo.get_thread_by_id(thread_id)
        if not thread:
            raise NotFoundError(ErrorMessages.CHAT_THREAD_NOT_FOUND)

        # Verify user has access to this thread
        if user_id != thread.user_a_id and user_id != thread.user_b_id:
            raise NotFoundError(ErrorMessages.CHAT_THREAD_NOT_FOUND)

        return await self.chat_repo.mark_messages_as_read(thread_id, user_id)

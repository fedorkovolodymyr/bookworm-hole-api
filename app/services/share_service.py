from uuid import UUID

from app.core.errors import ErrorMessages, NotFoundError, UnauthorizedError
from app.models.chat import ChatMessage
from app.repositories.book_repository import BookRepository
from app.repositories.collection_repository import CollectionRepository
from app.schemas.chat_schemas import SendChatMessageSchema
from app.services.chat_service import ChatService


class ShareService:
    def __init__(
        self,
        chat_service: ChatService,
        book_repo: BookRepository,
        collection_repo: CollectionRepository,
    ) -> None:
        self.chat_service = chat_service
        self.book_repo = book_repo
        self.collection_repo = collection_repo

    async def share_book(
        self,
        sender_id: UUID,
        book_id: UUID,
        friend_id: UUID,
        message_text: str,
    ) -> ChatMessage:
        """Share a book with a friend by sending a chat message with book attachment.

        Books have no visibility restriction — anyone can share them.
        `ChatService.send_message` verifies the two users are friends.
        """
        book = await self.book_repo.get_by_id(book_id)
        if not book:
            raise NotFoundError(ErrorMessages.BOOK_NOT_FOUND)

        data = SendChatMessageSchema(
            body=message_text,
            attachment_book_id=book_id,
        )
        return await self.chat_service.send_message(sender_id, friend_id, data)

    async def share_collection(
        self,
        sender_id: UUID,
        collection_id: UUID,
        friend_id: UUID,
        message_text: str,
    ) -> ChatMessage:
        """Share a collection with a friend by sending a chat message with a
        collection attachment.

        Authorization: collection must be public OR sender is the owner.
        `ChatService.send_message` verifies the two users are friends.
        """
        collection = await self.collection_repo.get_by_id(collection_id)
        if not collection:
            raise NotFoundError(ErrorMessages.COLLECTION_NOT_FOUND)

        if not collection.is_public and collection.user_id != sender_id:
            raise UnauthorizedError(ErrorMessages.USER_BLOCKED)

        data = SendChatMessageSchema(
            body=message_text,
            attachment_collection_id=collection_id,
        )
        return await self.chat_service.send_message(sender_id, friend_id, data)

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.deps import get_current_user
from app.models.user import User
from app.repositories.book_repository import BookRepository
from app.repositories.chat_repository import ChatRepository
from app.repositories.collection_repository import CollectionRepository
from app.repositories.friendship_repository import FriendshipRepository
from app.schemas.chat_schemas import ChatMessageResponse
from app.schemas.share_schemas import ShareBookSchema, ShareCollectionSchema
from app.services.chat_service import ChatService
from app.services.share_service import ShareService

share_router = APIRouter(prefix="/share", tags=["share"])


def get_share_service(
    session: AsyncSession = Depends(get_session),
) -> ShareService:
    chat_service = ChatService(ChatRepository(session), FriendshipRepository(session))
    return ShareService(
        chat_service,
        BookRepository(session),
        CollectionRepository(session),
    )


@share_router.post(
    "/book/{book_id}",
    response_model=ChatMessageResponse,
)
async def share_book(
    book_id: UUID,
    data: ShareBookSchema,
    current_user: User = Depends(get_current_user),
    service: ShareService = Depends(get_share_service),
):
    return await service.share_book(
        current_user.id, book_id, data.friend_id, data.message
    )


@share_router.post(
    "/collection/{collection_id}",
    response_model=ChatMessageResponse,
)
async def share_collection(
    collection_id: UUID,
    data: ShareCollectionSchema,
    current_user: User = Depends(get_current_user),
    service: ShareService = Depends(get_share_service),
):
    return await service.share_collection(
        current_user.id, collection_id, data.friend_id, data.message
    )

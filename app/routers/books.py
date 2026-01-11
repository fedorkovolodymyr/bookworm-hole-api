from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.services.book_service import BookService

books_router = APIRouter(prefix="/books", tags=["books"])


@books_router.get("/")
async def health_check(session: AsyncSession = Depends(get_session)):
    service = BookService()
    books = await service.get_all(session)
    return books

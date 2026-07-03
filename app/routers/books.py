from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.deps import require_admin
from app.repositories.book_repository import BookRepository
from app.schemas.book_schemas import (
    BookResponse,
    BookWithReleasesResponse,
    CreateBookSchema,
    UpdateBookSchema,
)
from app.schemas.common_schemas import Page
from app.services.book_service import BookService

books_router = APIRouter(prefix="/books", tags=["books"])


def get_book_service(session: AsyncSession = Depends(get_session)) -> BookService:
    return BookService(BookRepository(session))


@books_router.get("/", response_model=Page[BookResponse])
async def retrieve_all_books(
    skip: int = 0,
    limit: int = 10,
    title: str | None = None,
    author: str | None = None,
    language: str | None = None,
    service: BookService = Depends(get_book_service),
):
    return await service.retrieve_all_books(skip, limit, title, author, language)


@books_router.post(
    "/",
    response_model=BookResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_admin)],
)
async def create_book(
    new_book: CreateBookSchema,
    service: BookService = Depends(get_book_service),
):
    return await service.create_book(new_book)


@books_router.get("/by-isbn/{isbn}", response_model=BookWithReleasesResponse)
async def retrieve_book_by_isbn(
    isbn: str,
    service: BookService = Depends(get_book_service),
):
    return await service.retrieve_book_by_isbn(isbn)


@books_router.get("/{book_id}", response_model=BookWithReleasesResponse)
async def retrieve_book_by_id(
    book_id: UUID,
    service: BookService = Depends(get_book_service),
):
    return await service.retrieve_book_by_id(book_id)


@books_router.patch(
    "/{book_id}",
    response_model=BookResponse,
    dependencies=[Depends(require_admin)],
)
async def modify_book(
    book_id: UUID,
    updated_book: UpdateBookSchema,
    service: BookService = Depends(get_book_service),
):
    return await service.modify_book(book_id, updated_book)


@books_router.delete("/{book_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_book(
    book_id: UUID,
    service: BookService = Depends(get_book_service),
) -> None:
    await service.delete_book(book_id)

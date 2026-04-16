from typing import Sequence
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.models.books import Book
from app.repositories.boock_repository import BookRepository
from app.schemas.book_schemas import CreateBookSchema, UpdateBookSchema
from app.services.book_service import BookService

books_router = APIRouter(prefix="/books", tags=["books"])


async def get_book_repository(
    session: AsyncSession = Depends(get_session),
) -> BookRepository:
    return BookRepository(session)


async def get_book_service(
    repository: BookRepository = Depends(get_book_repository),
) -> BookService:
    return BookService(repository)


@books_router.get("/")
async def retrieve_all_books(
    service: BookService = Depends(get_book_service),
) -> Sequence[Book]:
    books = await service.retrieve_all_books()
    return books


@books_router.post("/")
async def create_book(
    new_book: CreateBookSchema, service: BookService = Depends(get_book_service)
) -> Book:
    created_book = await service.create_book(new_book)
    return created_book


@books_router.get("/{book_id}")
async def retrieve_book_by_id(
    book_id: int,
    service: BookService = Depends(get_book_service),
) -> Book | None:
    book = await service.retrieve_book_by_id(book_id)
    return book

@books_router.patch("/{book_id}")
async def modify_book(
    book_id: int,
    updated_book: UpdateBookSchema,
    service: BookService = Depends(get_book_service),
) -> Book | None:
    modified_book = await service.modify_book(book_id, updated_book)
    return modified_book


# @books_router.put("/{book_id}")
# async def replace_book(
#     book_id: int,
#     updated_book: CreateBookSchema,
#     service: BookService = Depends(get_book_service),
# ) -> Book:
#     replaced_book = await service.replace_book(book_id, updated_book)
#     return replaced_book
    

from typing import Sequence
from uuid import UUID

from fastapi import HTTPException

from app.models.books import Book
from app.repositories.book_repository import BookRepository
from app.schemas.book_schemas import CreateBookSchema, UpdateBookSchema


class BookService:
    def __init__(self, repository: BookRepository):
        self.repository = repository

    async def create_book(self, new_book: CreateBookSchema) -> Book:
        book = Book(**new_book.model_dump())
        return await self.repository.create(book)

    async def retrieve_book_by_id(self, book_id: UUID) -> Book:
        book = await self.repository.get_by_id(book_id)
        if not book:
            raise HTTPException(status_code=404, detail="Book not found")
        return book

    async def retrieve_all_books(self, skip: int = 0, limit: int = 10) -> Sequence[Book]:
        return await self.repository.get_all(skip, limit)

    async def modify_book(self, book_id: UUID, updated_book: UpdateBookSchema) -> Book:
        book = await self.repository.update(
            book_id, updated_book.model_dump(exclude_unset=True)
        )
        if not book:
            raise HTTPException(status_code=404, detail="Book not found")
        return book

    async def delete_book(self, book_id: UUID) -> None:
        deleted = await self.repository.delete(book_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Book not found")

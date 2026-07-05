from uuid import UUID

from fastapi import HTTPException

from app.core.errors import ConflictError, ErrorMessages, NotFoundError
from app.models.catalog import Book
from app.repositories.book_repository import BookRepository
from app.schemas.book_schemas import CreateBookSchema, UpdateBookSchema
from app.schemas.common_schemas import Page
from app.services.isbn import normalize_isbn


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

    async def retrieve_book_by_isbn(self, raw_isbn: str) -> Book:
        try:
            code_normalized = normalize_isbn(raw_isbn)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail="Book not found") from exc
        book = await self.repository.get_by_isbn(code_normalized)
        if not book:
            raise HTTPException(status_code=404, detail="Book not found")
        return book

    async def retrieve_all_books(
        self,
        skip: int = 0,
        limit: int = 10,
        title: str | None = None,
        author: str | None = None,
        language: str | None = None,
    ) -> Page[Book]:
        items, total = await self.repository.get_all(
            skip, limit, title, author, language
        )
        return Page(items=list(items), total=total, limit=limit, offset=skip)

    async def modify_book(self, book_id: UUID, updated_book: UpdateBookSchema) -> Book:
        book = await self.repository.update(book_id, updated_book)
        if not book:
            raise HTTPException(status_code=404, detail="Book not found")
        return book

    async def delete_book(self, book_id: UUID) -> None:
        deleted = await self.repository.delete(book_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Book not found")

    async def merge_books(self, source_id: UUID, target_id: UUID) -> Book:
        if source_id == target_id:
            raise ConflictError(ErrorMessages.CANNOT_MERGE_BOOK_INTO_ITSELF)
        merged = await self.repository.merge(source_id, target_id)
        if not merged:
            raise NotFoundError(ErrorMessages.BOOK_NOT_FOUND)
        return merged

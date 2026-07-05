from uuid import UUID

from fastapi import HTTPException

from app.models.catalog import Book
from app.repositories.book_repository import BookRepository
from app.repositories.review_repository import ReviewRepository
from app.schemas.book_schemas import (
    BookWithReleasesResponse,
    CreateBookSchema,
    ReleaseWithISBNsResponse,
    UpdateBookSchema,
)
from app.schemas.common_schemas import Page
from app.services.isbn import normalize_isbn


class BookService:
    def __init__(
        self, repository: BookRepository, review_repository: ReviewRepository
    ) -> None:
        self.repository = repository
        self.review_repository = review_repository

    async def create_book(self, new_book: CreateBookSchema) -> Book:
        book = Book(**new_book.model_dump())
        return await self.repository.create(book)

    async def retrieve_book_by_id(self, book_id: UUID) -> BookWithReleasesResponse:
        book = await self.repository.get_by_id(book_id)
        if not book:
            raise HTTPException(status_code=404, detail="Book not found")

        (
            avg_rating,
            rating_count,
        ) = await self.review_repository.get_rating_aggregate_for_book(book_id)

        releases: list[ReleaseWithISBNsResponse] = []
        for release in book.releases:
            (
                rel_avg,
                rel_count,
            ) = await self.review_repository.get_rating_aggregate_for_release(
                release.id
            )
            releases.append(
                ReleaseWithISBNsResponse.model_validate(release).model_copy(
                    update={"average_rating": rel_avg, "rating_count": rel_count}
                )
            )

        return BookWithReleasesResponse.model_validate(book).model_copy(
            update={
                "average_rating": avg_rating,
                "rating_count": rating_count,
                "releases": releases,
            }
        )

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

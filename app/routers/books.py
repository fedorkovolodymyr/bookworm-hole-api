from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.deps import require_admin
from app.repositories.book_repository import BookRepository
from app.repositories.review_repository import ReviewRepository, ReviewSort
from app.routers.responses import ADMIN_RESPONSES, CONFLICT_RESPONSE, NOT_FOUND_RESPONSE
from app.schemas.book_schemas import (
    BookResponse,
    BookWithReleasesResponse,
    CreateBookSchema,
    UpdateBookSchema,
)
from app.schemas.common_schemas import Page
from app.schemas.contributor_schemas import AddContributorSchema
from app.schemas.review_schemas import ReviewResponse
from app.services.book_service import BookService
from app.services.review_service import ReviewService

books_router = APIRouter(prefix="/books", tags=["books"])


def get_book_service(session: AsyncSession = Depends(get_session)) -> BookService:
    return BookService(BookRepository(session), ReviewRepository(session))


def get_review_service(
    session: AsyncSession = Depends(get_session),
) -> ReviewService:
    return ReviewService(ReviewRepository(session))


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


@books_router.delete(
    "/{book_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_admin)],
)
async def delete_book(
    book_id: UUID,
    service: BookService = Depends(get_book_service),
) -> None:
    await service.delete_book(book_id)


@books_router.post(
    "/{source_id}/merge-into/{target_id}",
    response_model=BookWithReleasesResponse,
    dependencies=[Depends(require_admin)],
    responses=ADMIN_RESPONSES | NOT_FOUND_RESPONSE | CONFLICT_RESPONSE,
    summary="Merge a duplicate book into another",
)
async def merge_book(
    source_id: UUID,
    target_id: UUID,
    service: BookService = Depends(get_book_service),
):
    """Reassign all releases, reviews, statuses, and collection items from
    `source_id` to `target_id`, then delete `source_id`. Atomic — a failure
    rolls back the whole merge.
    """
    return await service.merge_books(source_id, target_id)


@books_router.post(
    "/{book_id}/contributors",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_admin)],
    responses=ADMIN_RESPONSES | NOT_FOUND_RESPONSE,
)
async def add_book_contributor(
    book_id: UUID,
    payload: AddContributorSchema,
    service: BookService = Depends(get_book_service),
) -> dict[str, str]:
    """Add a contributor to a book. Returns 200 if already existed, 201 if newly
    created."""
    created = await service.add_contributor(
        book_id, payload.contributor_id, payload.role
    )
    return {"status": "created" if created else "already_existed"}


@books_router.delete(
    "/{book_id}/contributors/{contributor_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_admin)],
    responses=ADMIN_RESPONSES | NOT_FOUND_RESPONSE,
)
async def remove_book_contributor(
    book_id: UUID,
    contributor_id: UUID,
    role: str,
    service: BookService = Depends(get_book_service),
) -> None:
    from app.models.catalog import ContributorRole

    role_enum = ContributorRole(role)
    await service.remove_contributor(book_id, contributor_id, role_enum)


@books_router.get("/{book_id}/reviews", response_model=Page[ReviewResponse])
async def retrieve_book_reviews(
    book_id: UUID,
    sort: ReviewSort = "created_at",
    skip: int = 0,
    limit: int = 10,
    service: ReviewService = Depends(get_review_service),
):
    return await service.list_for_book(book_id, sort, skip, limit)

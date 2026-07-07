import csv
import io
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.deps import get_current_user
from app.models.user import User
from app.repositories.book_repository import BookRepository
from app.repositories.book_status_repository import BookStatusRepository
from app.repositories.collection_repository import CollectionRepository
from app.repositories.contributor_repository import ContributorRepository
from app.repositories.friendship_repository import FriendshipRepository
from app.repositories.import_repository import ImportRepository
from app.repositories.reading_session_repository import ReadingSessionRepository
from app.repositories.review_repository import ReviewRepository, ReviewSort
from app.repositories.user_repository import UserRepository
from app.schemas.common_schemas import Page
from app.schemas.export_schemas import AccountExportResponse
from app.schemas.import_schemas import ImportReportSchema
from app.schemas.review_schemas import ReviewResponse
from app.schemas.user_schemas import (
    ChangePasswordSchema,
    PublicUserProfileResponse,
    UpdateUserSchema,
    UserProfileResponse,
)
from app.services.book_status_service import BookStatusService
from app.services.import_service import ImportService
from app.services.review_service import ReviewService
from app.services.user_export_service import UserExportService
from app.services.user_service import UserService

users_router = APIRouter(prefix="/users", tags=["users"])


def get_book_status_service(
    session: AsyncSession = Depends(get_session),
) -> BookStatusService:
    return BookStatusService(BookStatusRepository(session))


def get_review_service(
    session: AsyncSession = Depends(get_session),
) -> ReviewService:
    return ReviewService(ReviewRepository(session))


def get_user_service(session: AsyncSession = Depends(get_session)) -> UserService:
    return UserService(UserRepository(session), CollectionRepository(session))


def get_import_service(session: AsyncSession = Depends(get_session)) -> ImportService:
    return ImportService(
        session,
        BookRepository(session),
        ContributorRepository(session),
        ImportRepository(session),
        BookStatusRepository(session),
    )


def get_export_service(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> UserExportService:
    return UserExportService(
        current_user,
        CollectionRepository(session),
        BookStatusRepository(session),
        ReviewRepository(session),
        ReadingSessionRepository(session),
        FriendshipRepository(session),
    )


@users_router.get("/me", response_model=UserProfileResponse)
async def retrieve_own_profile(current_user: User = Depends(get_current_user)):
    return current_user


@users_router.patch("/me", response_model=UserProfileResponse)
async def update_own_profile(
    data: UpdateUserSchema,
    current_user: User = Depends(get_current_user),
    service: UserService = Depends(get_user_service),
):
    return await service.update_profile(current_user.id, data)


@users_router.post("/me/password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(
    data: ChangePasswordSchema,
    current_user: User = Depends(get_current_user),
    service: UserService = Depends(get_user_service),
) -> None:
    """Change password. Requires the current password."""
    await service.change_password(current_user.id, data)


@users_router.post("/me/deactivate", response_model=UserProfileResponse)
async def deactivate_own_account(
    current_user: User = Depends(get_current_user),
    service: UserService = Depends(get_user_service),
):
    """Soft-deactivate the account. Reversible by an admin."""
    return await service.deactivate(current_user.id)


@users_router.get("/me/export/library.csv")
async def export_library_csv(
    current_user: User = Depends(get_current_user),
    service: BookStatusService = Depends(get_book_status_service),
) -> StreamingResponse:
    """Export user's library as CSV download."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"library_{timestamp}.csv"
    return StreamingResponse(
        service.export_library_csv(current_user.id),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@users_router.get("/{username}", response_model=PublicUserProfileResponse)
async def retrieve_public_profile(
    username: str,
    skip: int = 0,
    limit: int = 10,
    service: UserService = Depends(get_user_service),
):
    """Public profile: display name, bio, and public collections only."""
    return await service.get_public_profile(username, skip, limit)


@users_router.get("/{user_id}/reviews", response_model=Page[ReviewResponse])
async def retrieve_user_reviews(
    user_id: UUID,
    sort: ReviewSort = "created_at",
    skip: int = 0,
    limit: int = 10,
    service: ReviewService = Depends(get_review_service),
):
    """List a user's public reviews."""
    return await service.list_public_for_user(user_id, sort, skip, limit)


@users_router.post("/me/import/bookshelf", response_model=ImportReportSchema)
async def import_bookshelf_library(
    file: UploadFile,
    current_user: User = Depends(get_current_user),
    service: ImportService = Depends(get_import_service),
):
    """Import library from Bookshelf app export CSV."""
    content = await file.read()
    text = content.decode("utf-8")
    reader = csv.DictReader(io.StringIO(text))

    if not reader.fieldnames:
        from app.core.errors import AppError

        raise AppError("Invalid CSV format")

    rows = list(reader)
    column_mapping = {
        "title": "title",
        "author": "author",
        "isbn": "isbn",
        "status": "status",
        "date_added": "date_added",
    }

    return await service.import_rows(
        user_id=current_user.id,
        rows=rows,
        column_mapping=column_mapping,
        source_type="bookshelf",
    )


@users_router.post("/me/import/csv", response_model=ImportReportSchema)
async def import_generic_csv(
    file: UploadFile,
    title_col: str = "title",
    author_col: str = "author",
    isbn_col: str = "isbn",
    status_col: str = "status",
    date_added_col: str = "date_added",
    current_user: User = Depends(get_current_user),
    service: ImportService = Depends(get_import_service),
):
    """Import library from generic CSV with configurable column mapping."""
    content = await file.read()
    text = content.decode("utf-8")
    reader = csv.DictReader(io.StringIO(text))

    if not reader.fieldnames:
        from app.core.errors import AppError

        raise AppError("Invalid CSV format")

    rows = list(reader)
    column_mapping = {
        "title": title_col,
        "author": author_col,
        "isbn": isbn_col,
        "status": status_col,
        "date_added": date_added_col,
    }

    return await service.import_rows(
        user_id=current_user.id,
        rows=rows,
        column_mapping=column_mapping,
        source_type="csv",
    )


@users_router.post("/me/import/goodreads", response_model=ImportReportSchema)
async def import_goodreads_library(
    file: UploadFile,
    current_user: User = Depends(get_current_user),
    service: ImportService = Depends(get_import_service),
):
    """Import library from Goodreads export CSV."""
    content = await file.read()
    text = content.decode("utf-8")
    reader = csv.DictReader(io.StringIO(text))

    if not reader.fieldnames:
        from app.core.errors import AppError

        raise AppError("Invalid CSV format")

    rows = list(reader)
    column_mapping = {
        "title": "Title",
        "author": "Author",
        "isbn": "ISBN",
        "status": "Exclusive Shelf",
        "date_added": "Date Read",
    }

    return await service.import_rows(
        user_id=current_user.id,
        rows=rows,
        column_mapping=column_mapping,
        source_type="goodreads",
    )


@users_router.get("/me/export/all.json", response_model=AccountExportResponse)
async def export_account(
    service: UserExportService = Depends(get_export_service),
):
    """Export complete account data including profile, collections, and history."""
    return await service.export_account()

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.deps import require_admin
from app.repositories.book_repository import BookRepository
from app.repositories.contributor_repository import ContributorRepository
from app.repositories.import_repository import ImportRepository
from app.schemas.book_schemas import BookWithReleasesResponse, ImportBookRequest
from app.services.import_service import ImportService

external_router = APIRouter(prefix="/external", tags=["external"])


def get_import_service(
    session: AsyncSession = Depends(get_session),
) -> ImportService:
    return ImportService(
        session,
        BookRepository(session),
        ContributorRepository(session),
        ImportRepository(session),
    )


@external_router.post(
    "/import",
    response_model=BookWithReleasesResponse,
    dependencies=[Depends(require_admin)],
)
async def import_book(
    body: ImportBookRequest,
    service: ImportService = Depends(get_import_service),
):
    return await service.import_book(body.source, body.source_id)

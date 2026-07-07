from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.deps import require_admin
from app.models.catalog import Book
from app.repositories.book_repository import BookRepository
from app.repositories.contributor_repository import ContributorRepository
from app.repositories.import_repository import ImportRepository
from app.schemas.book_schemas import BookWithReleasesResponse, ImportBookRequest
from app.schemas.external_schemas import ExternalSearchResponse
from app.services.external_search_service import ExternalSearchService
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


def get_external_search_service(
    session: AsyncSession = Depends(get_session),
) -> ExternalSearchService:
    return ExternalSearchService(session)


@external_router.get(
    "/search",
    response_model=ExternalSearchResponse,
    summary="Search multiple external sources",
)
async def search_external(
    q: str,
    sources: str | None = None,
    service: ExternalSearchService = Depends(get_external_search_service),
) -> ExternalSearchResponse:
    source_list = sources.split(",") if sources else None
    return await service.search_multi_source(q, source_list)


@external_router.post(
    "/import",
    response_model=BookWithReleasesResponse,
    dependencies=[Depends(require_admin)],
)
async def import_book(
    body: ImportBookRequest,
    service: ImportService = Depends(get_import_service),
) -> Book:
    return await service.import_book(body.source, body.source_id)

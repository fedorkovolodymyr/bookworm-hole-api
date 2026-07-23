from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.models.catalog import Book
from app.repositories.book_repository import BookRepository
from app.repositories.contributor_repository import ContributorRepository
from app.repositories.import_repository import ImportRepository
from app.services.catalog_import_profiles import CatalogImportProfile
from app.services.external_search_service import ExternalSearchService
from app.services.import_service import ImportService


@dataclass(frozen=True)
class CatalogImportSummary:
    profile: str
    target_count: int
    imported: int
    attempted: int
    failed: int


class CatalogImportService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.search_service = ExternalSearchService(session)
        self.import_service = ImportService(
            session,
            BookRepository(session),
            ContributorRepository(session),
            ImportRepository(session),
        )

    async def run_profile(self, profile: CatalogImportProfile) -> CatalogImportSummary:
        before_count = await self._book_count()
        attempted = 0
        failed = 0

        for query in profile.queries:
            imported_so_far = await self._book_count() - before_count
            if imported_so_far >= profile.target_count:
                break

            response = await self.search_service.search_multi_source(
                query.text, query.sources
            )
            for hit in response.hits:
                attempted += 1
                try:
                    await self.import_service.import_book(hit.source, hit.source_id)
                except AppError:
                    failed += 1

        imported = await self._book_count() - before_count
        return CatalogImportSummary(
            profile=profile.name,
            target_count=profile.target_count,
            imported=imported,
            attempted=attempted,
            failed=failed,
        )

    async def _book_count(self) -> int:
        result = await self.session.execute(select(func.count()).select_from(Book))
        return result.scalar_one()

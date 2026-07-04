from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.catalog import Book, Contributor, ContributorRole
from app.repositories.book_repository import BookRepository
from app.repositories.contributor_repository import ContributorRepository
from app.repositories.import_repository import ImportRepository
from app.services.external.base import ExternalBookDetail, ExternalISBN
from app.services.external.registry import AdapterNotFoundError, get_adapter
from app.services.isbn import normalize_isbn


def _sort_name(full_name: str) -> str:
    parts = full_name.split()
    if len(parts) < 2:
        return full_name
    return f"{parts[-1]}, {' '.join(parts[:-1])}"


class ImportService:
    def __init__(
        self,
        session: AsyncSession,
        book_repository: BookRepository,
        contributor_repository: ContributorRepository,
        import_repository: ImportRepository,
    ) -> None:
        self.session = session
        self.book_repository = book_repository
        self.contributor_repository = contributor_repository
        self.import_repository = import_repository

    async def import_book(self, source: str, source_id: str) -> Book:
        try:
            adapter = get_adapter(source)
        except AdapterNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

        detail = await adapter.get_detail(source_id, self.session)
        if detail is None:
            raise HTTPException(status_code=404, detail="Source book not found")

        normalized_isbns = self._normalize_isbns(detail)

        book: Book | None = None
        for code, _ in normalized_isbns:
            book = await self.book_repository.get_by_isbn(code)
            if book:
                break
        found_by_isbn = book is not None

        contributors = await self._resolve_contributors(detail)

        if not found_by_isbn:
            contributor_ids = [contributor.id for contributor, _ in contributors]
            book = await self.import_repository.find_book_by_title_and_contributors(
                detail.title, contributor_ids
            )

        resolved_book: Book = book or await self.import_repository.add_book(
            title=detail.title,
            description=detail.description or "",
            first_publication_year=detail.published_year,
        )

        for contributor, role in contributors:
            await self.import_repository.link_book_contributor(
                resolved_book.id, contributor.id, role
            )

        if not found_by_isbn:
            release = await self.import_repository.add_release(
                book_id=resolved_book.id,
                format=detail.format,
                publisher=detail.publisher or "",
                published_year=detail.published_year,
                language=detail.language or "",
            )
            for code, ext_isbn in normalized_isbns:
                await self.import_repository.add_isbn(
                    release_id=release.id,
                    code_normalized=code,
                    code_original=ext_isbn.code,
                    kind=ext_isbn.kind,
                )
            for contributor, role in contributors:
                await self.import_repository.link_release_contributor(
                    release.id, contributor.id, role
                )

        reloaded = await self.book_repository.get_by_id(resolved_book.id)
        if reloaded is None:
            raise HTTPException(status_code=500, detail="Failed to import book")
        return reloaded

    async def _resolve_contributors(
        self, detail: ExternalBookDetail
    ) -> list[tuple[Contributor, ContributorRole]]:
        resolved: list[tuple[Contributor, ContributorRole]] = []
        for ext in detail.contributors:
            sort_name = _sort_name(ext.full_name)
            contributor = await self.contributor_repository.get_by_name(
                ext.full_name, sort_name
            )
            if contributor is None:
                contributor = await self.contributor_repository.add(
                    ext.full_name, sort_name
                )
            resolved.append((contributor, ext.role))
        return resolved

    @staticmethod
    def _normalize_isbns(
        detail: ExternalBookDetail,
    ) -> list[tuple[str, ExternalISBN]]:
        normalized: list[tuple[str, ExternalISBN]] = []
        for ext_isbn in detail.isbns:
            try:
                normalized.append((normalize_isbn(ext_isbn.code), ext_isbn))
            except ValueError:
                continue
        return normalized

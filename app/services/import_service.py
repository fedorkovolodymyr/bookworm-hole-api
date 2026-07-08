import contextlib
import hashlib
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError, ErrorMessages, NotFoundError
from app.models.book_status import BookStatus, BookStatusKind
from app.models.catalog import Book, Contributor, ContributorRole
from app.repositories.book_repository import BookRepository
from app.repositories.book_status_repository import BookStatusRepository
from app.repositories.contributor_repository import ContributorRepository
from app.repositories.import_repository import ImportRepository
from app.schemas.import_schemas import ImportReportSchema, ImportRowResultSchema
from app.services.external.base import (
    BookSourceAdapter,
    ExternalBookDetail,
    ExternalISBN,
)
from app.services.external.registry import get_adapter
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
        book_status_repository: BookStatusRepository | None = None,
    ) -> None:
        self.session = session
        self.book_repository = book_repository
        self.contributor_repository = contributor_repository
        self.import_repository = import_repository
        self.book_status_repository = book_status_repository

    async def import_book(self, source: str, source_id: str) -> Book:
        adapter = get_adapter(source)
        detail = await self._fetch_detail(adapter, source_id)

        normalized_isbns = self._normalize_isbns(detail)
        contributors = await self._resolve_contributors(detail)

        book, found_by_isbn = await self._resolve_book(
            detail, normalized_isbns, contributors
        )

        for contributor, role in contributors:
            await self.import_repository.link_book_contributor(
                book.id, contributor.id, role
            )

        if not found_by_isbn:
            await self._create_release(book, detail, normalized_isbns, contributors)

        return await self._reload_book(book.id)

    async def import_rows(
        self,
        user_id: UUID,
        rows: list[dict[str, str]],
        column_mapping: dict[str, str],
        source_type: str = "bookshelf",
        file_hash: str | None = None,
    ) -> ImportReportSchema:
        created_count = 0
        matched_count = 0
        skipped_count = 0
        failed_count = 0
        failures: list[ImportRowResultSchema] = []

        if not file_hash and rows:
            file_hash = self._compute_file_hash(rows)

        for row_index, row in enumerate(rows):
            try:
                result = await self._process_import_row(
                    user_id, row_index, row, column_mapping
                )
                if result.status == "created":
                    created_count += 1
                elif result.status == "matched":
                    matched_count += 1
                elif result.status == "skipped":
                    skipped_count += 1
                elif result.status == "failed":
                    failed_count += 1
                    failures.append(result)
            except AppError as e:
                failed_count += 1
                failures.append(
                    ImportRowResultSchema(
                        row_index=row_index,
                        status="failed",
                        reason=str(e),
                    )
                )

        if file_hash:
            await self.import_repository.create_import_record(
                user_id=user_id,
                file_hash=file_hash,
                row_count=len(rows),
                source_type=source_type,
            )

        return ImportReportSchema(
            created=created_count,
            matched=matched_count,
            skipped=skipped_count,
            failed=failed_count,
            total=len(rows),
            failures=failures,
        )

    async def _process_import_row(
        self,
        user_id: UUID,
        row_index: int,
        row: dict[str, str],
        column_mapping: dict[str, str],
    ) -> ImportRowResultSchema:
        title = row.get(column_mapping.get("title", "title"), "").strip()
        author = row.get(column_mapping.get("author", "author"), "").strip()
        isbn = row.get(column_mapping.get("isbn", "isbn"), "").strip()
        status_str = row.get(column_mapping.get("status", "status"), "owned").strip()
        date_added = row.get(column_mapping.get("date_added", "date_added"), "").strip()

        if not title:
            return ImportRowResultSchema(
                row_index=row_index,
                status="failed",
                reason="Missing title",
            )

        try:
            status = BookStatusKind(status_str)
        except ValueError:
            status = BookStatusKind.owned

        book = await self._resolve_book_from_row(title, author, isbn)
        if not book:
            return ImportRowResultSchema(
                row_index=row_index,
                status="skipped",
                reason="Could not resolve book",
            )

        existing = await self.import_repository.find_existing_status(
            user_id, book.id, None
        )
        if existing:
            return ImportRowResultSchema(
                row_index=row_index,
                status="matched",
                reason="BookStatus already exists for user",
                book_id=book.id,
            )

        acquired_at = None
        if date_added:
            with contextlib.suppress(ValueError, AttributeError):
                acquired_at = datetime.fromisoformat(date_added.replace("Z", "+00:00"))

        book_status = BookStatus(
            user_id=user_id,
            book_id=book.id,
            status=status,
            acquired_at=acquired_at or datetime.now(UTC),
        )
        self.session.add(book_status)
        await self.session.flush()

        return ImportRowResultSchema(
            row_index=row_index,
            status="created",
            reason="New BookStatus created",
            book_id=book.id,
        )

    async def _resolve_book_from_row(
        self, title: str, author: str, isbn: str | None
    ) -> Book | None:
        if isbn:
            try:
                normalized = normalize_isbn(isbn)
                book = await self.book_repository.get_by_isbn(normalized)
                if book:
                    return book
            except ValueError:
                pass

        if title and author:
            return await self.import_repository.find_book_by_title_and_contributors(
                title, []
            )

        return None

    @staticmethod
    def _compute_file_hash(rows: list[dict[str, str]]) -> str:
        content = repr(rows).encode("utf-8")
        return hashlib.sha256(content).hexdigest()

    async def _fetch_detail(
        self, adapter: BookSourceAdapter, source_id: str
    ) -> ExternalBookDetail:
        detail = await adapter.get_detail(source_id, self.session)
        if detail is None:
            raise NotFoundError(ErrorMessages.SOURCE_BOOK_NOT_FOUND)
        return detail

    async def _resolve_book(
        self,
        detail: ExternalBookDetail,
        normalized_isbns: list[tuple[str, ExternalISBN]],
        contributors: list[tuple[Contributor, ContributorRole]],
    ) -> tuple[Book, bool]:
        for code, _ in normalized_isbns:
            book = await self.book_repository.get_by_isbn(code)
            if book:
                return book, True

        contributor_ids = [contributor.id for contributor, _ in contributors]
        book = await self.import_repository.find_book_by_title_and_contributors(
            detail.title, contributor_ids
        )
        if book:
            return book, False

        book = await self.import_repository.add_book(
            title=detail.title,
            description=detail.description or "",
            first_publication_year=detail.published_year,
        )
        return book, False

    async def _create_release(
        self,
        book: Book,
        detail: ExternalBookDetail,
        normalized_isbns: list[tuple[str, ExternalISBN]],
        contributors: list[tuple[Contributor, ContributorRole]],
    ) -> None:
        release = await self.import_repository.add_release(
            book_id=book.id,
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

    async def _reload_book(self, book_id: UUID) -> Book:
        reloaded = await self.book_repository.get_by_id(book_id)
        if reloaded is None:
            raise AppError("Failed to import book")
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

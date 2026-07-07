import csv
import io
from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException

from app.core.errors import ExternalServiceError
from app.models.book_status import BookStatus, BookStatusKind
from app.repositories.book_status_repository import BookStatusRepository, BookStatusSort
from app.schemas.book_status_schemas import (
    CreateBookStatusSchema,
    LendBookStatusSchema,
    UpdateBookStatusSchema,
)
from app.schemas.common_schemas import Page


class BookStatusService:
    def __init__(self, repository: BookStatusRepository):
        self.repository = repository

    async def create_status(
        self, user_id: UUID, new_status: CreateBookStatusSchema
    ) -> BookStatus:
        book_status = BookStatus(
            user_id=user_id,
            acquired_at=datetime.now(UTC),
            **new_status.model_dump(),
        )
        return await self.repository.create(book_status)

    async def list_statuses(
        self, user_id: UUID, status: BookStatusKind | None = None
    ) -> list[BookStatus]:
        return list(await self.repository.get_all_for_user(user_id, status))

    async def list_page_by_kind(
        self,
        user_id: UUID,
        kind: BookStatusKind,
        sort: BookStatusSort = "acquired_at",
        skip: int = 0,
        limit: int = 10,
    ) -> Page[BookStatus]:
        items, total = await self.repository.get_page_for_user(
            user_id, kind, sort, skip, limit
        )
        return Page(items=list(items), total=total, limit=limit, offset=skip)

    async def _retrieve_owned(self, user_id: UUID, book_status_id: UUID) -> BookStatus:
        book_status = await self.repository.get_by_id(book_status_id)
        if not book_status or book_status.user_id != user_id:
            raise HTTPException(status_code=404, detail="Status not found")
        return book_status

    async def modify_status(
        self,
        user_id: UUID,
        book_status_id: UUID,
        updated_status: UpdateBookStatusSchema,
    ) -> BookStatus:
        await self._retrieve_owned(user_id, book_status_id)
        book_status = await self.repository.update(book_status_id, updated_status)
        if not book_status:
            raise HTTPException(status_code=404, detail="Status not found")
        return book_status

    async def delete_status(self, user_id: UUID, book_status_id: UUID) -> None:
        await self._retrieve_owned(user_id, book_status_id)
        deleted = await self.repository.delete(book_status_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Status not found")

    async def lend_status(
        self, user_id: UUID, book_status_id: UUID, lend: LendBookStatusSchema
    ) -> BookStatus:
        book_status = await self._retrieve_owned(user_id, book_status_id)
        if book_status.status != BookStatusKind.owned:
            raise HTTPException(
                status_code=409, detail="Only an owned status can be lent out"
            )
        book_status.status = BookStatusKind.lent_out
        book_status.lent_to_user_id = lend.lent_to_user_id
        book_status.lent_to_name = lend.lent_to_name
        book_status.lent_at = datetime.now(UTC)
        book_status.returned_at = None
        return await self.repository.save(book_status)

    async def return_status(self, user_id: UUID, book_status_id: UUID) -> BookStatus:
        book_status = await self._retrieve_owned(user_id, book_status_id)
        if book_status.status != BookStatusKind.lent_out:
            raise HTTPException(
                status_code=409, detail="Only a lent-out status can be returned"
            )
        book_status.status = BookStatusKind.owned
        book_status.returned_at = datetime.now(UTC)
        book_status.lent_to_user_id = None
        book_status.lent_to_name = None
        return await self.repository.save(book_status)

    async def export_library_csv(
        self,
        user_id: UUID,
    ) -> AsyncGenerator[str]:
        try:
            statuses = await self.repository.get_all_for_user_with_eager_load(user_id)

            output = io.StringIO()
            writer = csv.writer(output)
        except Exception as e:
            raise ExternalServiceError(f"Failed to export library: {e!s}") from e

        headers = [
            "book_title",
            "authors",
            "release_format",
            "publisher",
            "published_year",
            "language",
            "isbn",
            "status",
            "acquired_at",
            "notes",
        ]
        writer.writerow(headers)
        yield output.getvalue()
        output.truncate(0)
        output.seek(0)

        for status in statuses:
            book_title = ""
            authors = ""
            release_format = ""
            publisher = ""
            published_year = ""
            language = ""
            isbn = ""

            release = status.release
            book = status.book

            if release:
                book_title = release.book.title if release.book else ""
                release_format = release.format.value if release.format else ""
                publisher = release.publisher if release.publisher else ""
                published_year = (
                    str(release.published_year) if release.published_year else ""
                )
                language = release.language if release.language else ""

                if release.isbns:
                    isbn = release.isbns[0].code_normalized if release.isbns else ""

                contributors = release.contributors if release.contributors else []
                author_names = [
                    c.full_name
                    for c in contributors
                    if c and hasattr(c, "full_name") and c.full_name
                ]
                authors = "; ".join(author_names)
            elif book:
                book_title = book.title if book.title else ""

                if book.releases:
                    first_release = book.releases[0]
                    release_format = (
                        first_release.format.value if first_release.format else ""
                    )
                    publisher = (
                        first_release.publisher if first_release.publisher else ""
                    )
                    published_year = (
                        str(first_release.published_year)
                        if first_release.published_year
                        else ""
                    )
                    language = first_release.language if first_release.language else ""

                    if first_release.isbns:
                        isbn = first_release.isbns[0].code_normalized

                contributors = book.contributors if book.contributors else []
                author_names = [
                    c.full_name
                    for c in contributors
                    if c and hasattr(c, "full_name") and c.full_name
                ]
                authors = "; ".join(author_names)

            status_str = status.status.value if status.status else ""
            acquired_at_str = (
                status.acquired_at.isoformat() if status.acquired_at else ""
            )
            notes_str = status.notes if status.notes else ""

            row = [
                book_title,
                authors,
                release_format,
                publisher,
                published_year,
                language,
                isbn,
                status_str,
                acquired_at_str,
                notes_str,
            ]
            writer.writerow(row)
            yield output.getvalue()
            output.truncate(0)
            output.seek(0)

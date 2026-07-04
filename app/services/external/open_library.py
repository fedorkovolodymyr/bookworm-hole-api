import re
from typing import Any, cast

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.errors import ErrorMessages, ExternalServiceError
from app.models.catalog import ISBNKind, ReleaseFormat
from app.models.external_source import ExternalRefKind, ExternalSourceRecord
from app.repositories.external_source_repository import ExternalSourceRepository
from app.services.external.base import (
    BookSourceAdapter,
    ExternalBookDetail,
    ExternalContributor,
    ExternalISBN,
)
from app.services.external.registry import register_adapter

_FORMAT_BY_PHYSICAL_FORMAT = {
    "hardcover": ReleaseFormat.hardcover,
    "paperback": ReleaseFormat.paperback,
    "ebook": ReleaseFormat.ebook,
    "audiobook": ReleaseFormat.audiobook,
}


def _parse_format(physical_format: str | None) -> ReleaseFormat:
    if not physical_format:
        return ReleaseFormat.other
    return _FORMAT_BY_PHYSICAL_FORMAT.get(
        physical_format.strip().lower(), ReleaseFormat.other
    )


def _parse_published_year(publish_date: str | None) -> int | None:
    if not publish_date:
        return None
    match = re.search(r"\d{4}", publish_date)
    return int(match.group()) if match else None


def _parse_language(languages: list[dict[str, Any]] | None) -> str | None:
    if not languages:
        return None
    key: Any = languages[0].get("key", "")
    return key.rsplit("/", 1)[-1] or None


def _parse_cover_url(covers: list[int] | None) -> str | None:
    if not covers:
        return None
    return f"https://covers.openlibrary.org/b/id/{covers[0]}-L.jpg"


def _parse_description(work_doc: dict[str, Any]) -> str | None:
    raw: Any = work_doc.get("description")
    if isinstance(raw, dict):
        return cast(dict[str, Any], raw).get("value")
    if isinstance(raw, str):
        return raw
    return None


def _parse_contributors(isbn_doc: dict[str, Any]) -> list[ExternalContributor]:
    by_statement = isbn_doc.get("by_statement")
    if not by_statement:
        return []
    return [ExternalContributor(full_name=by_statement.strip())]


def _parse_isbns(isbn_doc: dict[str, Any]) -> list[ExternalISBN]:
    isbns = [
        ExternalISBN(code=code, kind=ISBNKind.isbn13)
        for code in isbn_doc.get("isbn_13", [])
    ]
    isbns += [
        ExternalISBN(code=code, kind=ISBNKind.isbn10)
        for code in isbn_doc.get("isbn_10", [])
    ]
    return isbns


@register_adapter("open_library")
class OpenLibraryAdapter(BookSourceAdapter):
    name = "open_library"

    def __init__(self) -> None:
        self._settings = settings.open_library_settings

    def _build_client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            base_url=self._settings.base_url,
            timeout=self._settings.timeout_seconds,
            transport=httpx.AsyncHTTPTransport(retries=self._settings.retries),
        )

    async def search(
        self, query: str, session: AsyncSession
    ) -> list[ExternalSourceRecord]:
        async with self._build_client() as client:
            try:
                response = await client.get("/search.json", params={"q": query})
                response.raise_for_status()
            except httpx.HTTPError as exc:
                raise ExternalServiceError(
                    ErrorMessages.EXTERNAL_LOOKUP_FAILED
                ) from exc
            docs = response.json().get("docs", [])

        repo = ExternalSourceRepository(session)
        return [
            await repo.create(
                source=self.name,
                ref_kind=ExternalRefKind.search,
                ref=query,
                payload=doc,
            )
            for doc in docs
        ]

    async def get_by_isbn(
        self, isbn: str, session: AsyncSession
    ) -> ExternalSourceRecord | None:
        async with self._build_client() as client:
            try:
                response = await client.get(f"/isbn/{isbn}.json")
                if response.status_code == int(httpx.codes.NOT_FOUND):
                    return None
                response.raise_for_status()
            except httpx.HTTPError as exc:
                raise ExternalServiceError(
                    ErrorMessages.EXTERNAL_LOOKUP_FAILED
                ) from exc
            isbn_doc = response.json()

            work_doc: dict[str, object] = {}
            works = isbn_doc.get("works", [])
            if works and works[0].get("key"):
                work_key = works[0]["key"]
                try:
                    work_response = await client.get(f"{work_key}.json")
                    if work_response.status_code != int(httpx.codes.NOT_FOUND):
                        work_response.raise_for_status()
                        work_doc = work_response.json()
                except httpx.HTTPError:
                    pass

        repo = ExternalSourceRepository(session)
        return await repo.create(
            source=self.name,
            ref_kind=ExternalRefKind.isbn,
            ref=isbn,
            payload={"isbn_doc": isbn_doc, "work_doc": work_doc},
        )

    async def get_detail(
        self, source_id: str, session: AsyncSession
    ) -> ExternalBookDetail | None:
        record = await self.get_by_isbn(source_id, session)
        if record is None:
            return None

        isbn_doc = record.payload.get("isbn_doc", {})
        work_doc = record.payload.get("work_doc", {})

        return ExternalBookDetail(
            title=isbn_doc.get("title") or work_doc.get("title") or "",
            description=_parse_description(work_doc),
            contributors=_parse_contributors(isbn_doc),
            isbns=_parse_isbns(isbn_doc),
            format=_parse_format(isbn_doc.get("physical_format")),
            publisher=next(iter(isbn_doc.get("publishers", [])), None),
            published_year=_parse_published_year(isbn_doc.get("publish_date")),
            language=_parse_language(isbn_doc.get("languages")),
            cover_image_url=_parse_cover_url(isbn_doc.get("covers")),
        )

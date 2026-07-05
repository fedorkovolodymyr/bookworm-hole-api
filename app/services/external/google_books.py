import re
from typing import Any

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

_ISBN_KIND_BY_TYPE = {
    "ISBN_13": ISBNKind.isbn13,
    "ISBN_10": ISBNKind.isbn10,
}


def _parse_published_year(published_date: str | None) -> int | None:
    if not published_date:
        return None
    match = re.match(r"\d{4}", published_date)
    return int(match.group()) if match else None


def _parse_contributors(authors: list[str] | None) -> list[ExternalContributor]:
    return [ExternalContributor(full_name=author) for author in authors or []]


def _parse_isbns(
    industry_identifiers: list[dict[str, Any]] | None,
) -> list[ExternalISBN]:
    isbns: list[ExternalISBN] = []
    for identifier in industry_identifiers or []:
        kind = _ISBN_KIND_BY_TYPE.get(identifier.get("type", ""))
        if kind is not None:
            isbns.append(ExternalISBN(code=identifier["identifier"], kind=kind))
    return isbns


def _parse_format(item: dict[str, Any]) -> ReleaseFormat:
    access_info: dict[str, Any] = item.get("accessInfo", {})
    epub_available = access_info.get("epub", {}).get("isAvailable", False)
    pdf_available = access_info.get("pdf", {}).get("isAvailable", False)
    if epub_available or pdf_available:
        return ReleaseFormat.ebook
    return ReleaseFormat.other


def _parse_cover_url(volume_info: dict[str, Any]) -> str | None:
    image_links: dict[str, Any] = volume_info.get("imageLinks", {})
    url = image_links.get("thumbnail") or image_links.get("smallThumbnail")
    return url.replace("http://", "https://") if url else None


@register_adapter("google_books")
class GoogleBooksAdapter(BookSourceAdapter):
    name = "google_books"

    def __init__(self) -> None:
        self._settings = settings.google_books_settings

    def _build_client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            base_url=self._settings.base_url,
            timeout=self._settings.timeout_seconds,
            transport=httpx.AsyncHTTPTransport(retries=self._settings.retries),
        )

    def _params(self, **extra: str) -> dict[str, str]:
        params = dict(extra)
        if self._settings.api_key:
            params["key"] = self._settings.api_key
        return params

    async def search(
        self, query: str, session: AsyncSession
    ) -> list[ExternalSourceRecord]:
        async with self._build_client() as client:
            try:
                response = await client.get("/volumes", params=self._params(q=query))
                response.raise_for_status()
            except httpx.HTTPError as exc:
                raise ExternalServiceError(
                    ErrorMessages.EXTERNAL_LOOKUP_FAILED
                ) from exc
            items = response.json().get("items", [])

        repo = ExternalSourceRepository(session)
        return [
            await repo.create(
                source=self.name,
                ref_kind=ExternalRefKind.search,
                ref=query,
                payload=item,
            )
            for item in items
        ]

    async def get_by_isbn(
        self, isbn: str, session: AsyncSession
    ) -> ExternalSourceRecord | None:
        async with self._build_client() as client:
            try:
                response = await client.get(
                    "/volumes", params=self._params(q=f"isbn:{isbn}")
                )
                response.raise_for_status()
            except httpx.HTTPError as exc:
                raise ExternalServiceError(
                    ErrorMessages.EXTERNAL_LOOKUP_FAILED
                ) from exc
            items = response.json().get("items", [])

        if not items:
            return None

        repo = ExternalSourceRepository(session)
        return await repo.create(
            source=self.name,
            ref_kind=ExternalRefKind.isbn,
            ref=isbn,
            payload=items[0],
        )

    async def get_detail(
        self, source_id: str, session: AsyncSession
    ) -> ExternalBookDetail | None:
        async with self._build_client() as client:
            try:
                response = await client.get(
                    f"/volumes/{source_id}", params=self._params()
                )
                if response.status_code == int(httpx.codes.NOT_FOUND):
                    return None
                response.raise_for_status()
            except httpx.HTTPError as exc:
                raise ExternalServiceError(
                    ErrorMessages.EXTERNAL_LOOKUP_FAILED
                ) from exc
            item = response.json()

        volume_info: dict[str, Any] = item.get("volumeInfo", {})
        return ExternalBookDetail(
            title=volume_info.get("title") or "",
            description=volume_info.get("description"),
            contributors=_parse_contributors(volume_info.get("authors")),
            isbns=_parse_isbns(volume_info.get("industryIdentifiers")),
            format=_parse_format(item),
            publisher=volume_info.get("publisher"),
            published_year=_parse_published_year(volume_info.get("publishedDate")),
            language=volume_info.get("language"),
            cover_image_url=_parse_cover_url(volume_info),
        )

import re
from typing import Any

import httpx

from app.core.config import settings
from app.models.catalog import ContributorRole, ISBNKind, ReleaseFormat
from app.services.external.base import (
    BookSourceAdapter,
    ExternalBookDetail,
    ExternalBookHit,
    ExternalContributor,
    ExternalISBN,
)
from app.services.external.registry import register_adapter

_FORMAT_MAP = {
    "hardcover": ReleaseFormat.hardcover,
    "paperback": ReleaseFormat.paperback,
    "mass market paperback": ReleaseFormat.paperback,
    "ebook": ReleaseFormat.ebook,
    "audiobook": ReleaseFormat.audiobook,
}

_YEAR_RE = re.compile(r"(\d{4})")


def _cover_url(cover_id: int | None, covers_base_url: str) -> str | None:
    if cover_id is None:
        return None
    return f"{covers_base_url}/b/id/{cover_id}-L.jpg"


def _classify_isbn(code: str) -> ISBNKind:
    digits = code.replace("-", "")
    if len(digits) == 13:
        return ISBNKind.isbn13
    if len(digits) == 10:
        return ISBNKind.isbn10
    return ISBNKind.other


def _parse_year(publish_date: str | None) -> int | None:
    if not publish_date:
        return None
    match = _YEAR_RE.search(publish_date)
    return int(match.group(1)) if match else None


def _parse_description(description: str | dict[str, Any] | None) -> str | None:
    if description is None:
        return None
    if isinstance(description, dict):
        return description.get("value")
    return description


def _doc_to_hit(doc: dict[str, Any]) -> ExternalBookHit:
    contributors = [
        ExternalContributor(full_name=name, role=ContributorRole.author)
        for name in doc.get("author_name", [])
    ]
    isbns = [
        ExternalISBN(code=code, kind=_classify_isbn(code))
        for code in doc.get("isbn", [])
    ]
    return ExternalBookHit(
        title=doc.get("title", ""),
        contributors=contributors,
        isbns=isbns,
        cover_image_url=_cover_url(
            doc.get("cover_i"), settings.open_library_settings.covers_base_url
        ),
        raw=doc,
    )


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

    async def search(self, query: str) -> list[ExternalBookHit]:
        async with self._build_client() as client:
            response = await client.get("/search.json", params={"q": query})
        response.raise_for_status()
        docs = response.json().get("docs", [])
        return [_doc_to_hit(doc) for doc in docs]

    async def get_by_isbn(self, isbn: str) -> ExternalBookDetail | None:
        async with self._build_client() as client:
            response = await client.get(f"/isbn/{isbn}.json")
            if response.status_code == httpx.codes.NOT_FOUND:
                return None
            response.raise_for_status()
            isbn_doc = response.json()

            work_doc: dict[str, Any] = {}
            works = isbn_doc.get("works", [])
            if works and works[0].get("key"):
                work_key = works[0]["key"]
                work_response = await client.get(f"{work_key}.json")
                if work_response.status_code != httpx.codes.NOT_FOUND:
                    work_response.raise_for_status()
                    work_doc = work_response.json()

        contributors = [
            ExternalContributor(
                full_name=isbn_doc.get("by_statement", "Unknown"),
                role=ContributorRole.author,
            )
        ]
        isbns = [
            ExternalISBN(code=code, kind=ISBNKind.isbn10)
            for code in isbn_doc.get("isbn_10", [])
        ] + [
            ExternalISBN(code=code, kind=ISBNKind.isbn13)
            for code in isbn_doc.get("isbn_13", [])
        ]
        languages = isbn_doc.get("languages", [])
        language_key = languages[0].get("key") if languages else None
        language = language_key.removeprefix("/languages/") if language_key else None
        cover_ids = isbn_doc.get("covers") or work_doc.get("covers") or []

        return ExternalBookDetail(
            title=isbn_doc.get("title") or work_doc.get("title", ""),
            description=_parse_description(work_doc.get("description")),
            contributors=contributors,
            isbns=isbns,
            format=_FORMAT_MAP.get(
                str(isbn_doc.get("physical_format", "")).lower(), ReleaseFormat.other
            ),
            publisher=(isbn_doc.get("publishers") or [None])[0],
            published_year=_parse_year(isbn_doc.get("publish_date")),
            language=language,
            cover_image_url=_cover_url(
                cover_ids[0] if cover_ids else None, self._settings.covers_base_url
            ),
            raw={"isbn_doc": isbn_doc, "work_doc": work_doc},
        )

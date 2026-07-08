import asyncio
from difflib import SequenceMatcher
from typing import Any, cast

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ErrorMessages, ExternalServiceError
from app.models.external_source import ExternalSourceRecord
from app.schemas.external_schemas import (
    ExternalSearchHit,
    ExternalSearchResponse,
)
from app.services.external import (
    get_adapter,
    get_all_adapter_names,
)
from app.services.isbn import normalize_isbn


def _normalize_isbn_safe(code: str) -> str | None:
    try:
        return normalize_isbn(code)
    except ValueError:
        return None


def _extract_hit_data(
    record: ExternalSourceRecord, source: str
) -> tuple[str, list[str], list[str], str | None, str | None]:
    """Extract title, isbns, authors, cover_url, and source_id from adapter record.

    Dispatches on payload shape (google_books nests fields under `volumeInfo`;
    every other adapter, including test stubs, uses the flatter open_library-style
    shape) rather than on the source name, so a newly registered adapter's hits
    aren't silently dropped.

    Returns (title, isbns, authors, cover_image_url, source_id)
    """
    payload = record.payload
    if "volumeInfo" in payload:
        volume_info: dict[str, Any] = payload.get("volumeInfo", {})
        isbns_result: list[str] = []
        for iid in volume_info.get("industryIdentifiers", []):
            normalized = _normalize_isbn_safe(iid.get("identifier", ""))
            if normalized:
                isbns_result.append(normalized)
        authors: list[str] = volume_info.get("authors", [])
        cover_url: str | None = None
        image_links: dict[str, Any] = volume_info.get("imageLinks", {})
        if image_links.get("thumbnail") or image_links.get("smallThumbnail"):
            url = image_links.get("thumbnail") or image_links.get("smallThumbnail")
            cover_url = url.replace("http://", "https://") if url else None
        return (
            volume_info.get("title", ""),
            isbns_result,
            authors,
            cover_url,
            payload.get("id", ""),
        )

    isbns: list[str] = []
    for code in payload.get("isbn_13", []) + payload.get("isbn_10", []):
        normalized = _normalize_isbn_safe(code)
        if normalized:
            isbns.append(normalized)
    author_name: Any = payload.get("author_name")
    authors: list[str]
    if isinstance(author_name, list):
        authors = [str(name) for name in cast("list[Any]", author_name)]
    elif author_name:
        authors = [str(author_name)]
    else:
        authors = []
    return (
        payload.get("title", ""),
        isbns,
        authors,
        None,
        payload.get("key", ""),
    )


def _similarity_ratio(s1: str, s2: str) -> float:
    """Calculate similarity between two strings (0-1)."""
    return SequenceMatcher(None, s1.lower(), s2.lower()).ratio()


def _deduplicate_hits(
    hits: list[tuple[ExternalSearchHit, str]],
) -> list[ExternalSearchHit]:
    """Deduplicate hits by ISBN, with fuzzy title+author fallback.

    Returns list of unique hits.
    """
    seen_isbns: set[str] = set()
    seen_fuzzy: list[tuple[str, str]] = []
    unique_hits: list[ExternalSearchHit] = []

    for hit, _ in hits:
        hit_isbns = hit.isbns
        is_duplicate_isbn = False

        for isbn in hit_isbns:
            if isbn in seen_isbns:
                is_duplicate_isbn = True
                break

        if is_duplicate_isbn:
            continue

        for title, authors_str in seen_fuzzy:
            if (
                _similarity_ratio(hit.title, title) > 0.8
                and _similarity_ratio(", ".join(hit.authors), authors_str) > 0.8
            ):
                is_duplicate_isbn = True
                break

        if not is_duplicate_isbn:
            seen_isbns.update(hit_isbns)
            seen_fuzzy.append((hit.title, ", ".join(hit.authors)))
            unique_hits.append(hit)

    return unique_hits


class ExternalSearchService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def search_multi_source(
        self, query: str, sources: list[str] | None = None
    ) -> ExternalSearchResponse:
        """Search multiple external sources in parallel.

        Args:
            query: Search query
            sources: List of adapter names. If None, search all available adapters.

        Returns:
            Merged and deduplicated results with partial failure info.
        """
        if sources is None:
            sources = get_all_adapter_names()

        tasks = [
            self._search_single_source(query, source_name) for source_name in sources
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        all_hits: list[tuple[ExternalSearchHit, str]] = []
        partial_failures: dict[str, str] = {}

        for source_name, result in zip(sources, results, strict=True):
            if isinstance(result, Exception):
                error_msg = getattr(result, "detail", str(result))
                partial_failures[source_name] = error_msg
            elif isinstance(result, list):
                for hit in result:
                    all_hits.append((hit, source_name))

        merged_hits = _deduplicate_hits(all_hits)

        return ExternalSearchResponse(
            query=query,
            hits=merged_hits,
            partial_failures=partial_failures,
        )

    async def _search_single_source(
        self, query: str, source_name: str
    ) -> list[ExternalSearchHit]:
        """Search a single source and convert results to ExternalSearchHit.

        Raises ExternalServiceError on adapter error.
        """
        try:
            adapter = get_adapter(source_name)
        except Exception as exc:
            raise ExternalServiceError(f"Adapter not found: {source_name}") from exc

        try:
            records = await adapter.search(query, self.session)
        except ExternalServiceError:
            raise
        except Exception as exc:
            raise ExternalServiceError(ErrorMessages.EXTERNAL_LOOKUP_FAILED) from exc

        hits: list[ExternalSearchHit] = []
        for record in records:
            title, isbns, authors, cover_url, _source_id = _extract_hit_data(
                record, source_name
            )
            if title:
                hits.append(
                    ExternalSearchHit(
                        source=source_name,
                        title=title,
                        isbns=isbns,
                        authors=authors,
                        cover_image_url=cover_url,
                    )
                )

        return hits

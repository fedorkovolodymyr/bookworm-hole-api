import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.external_source import ExternalRefKind, ExternalSourceRecord
from app.repositories.external_source_repository import ExternalSourceRepository
from app.services.external.base import BookSourceAdapter
from app.services.external.registry import register_adapter


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
            response = await client.get("/search.json", params={"q": query})
            response.raise_for_status()
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
            response = await client.get(f"/isbn/{isbn}.json")
            if response.status_code == httpx.codes.NOT_FOUND:
                return None
            response.raise_for_status()
            isbn_doc = response.json()

            work_doc: dict[str, object] = {}
            works = isbn_doc.get("works", [])
            if works and works[0].get("key"):
                work_key = works[0]["key"]
                try:
                    work_response = await client.get(f"{work_key}.json")
                    if work_response.status_code != httpx.codes.NOT_FOUND:
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

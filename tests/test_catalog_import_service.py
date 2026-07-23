from typing import ClassVar

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.catalog import ReleaseFormat
from app.models.external_source import ExternalRefKind, ExternalSourceRecord
from app.repositories.external_source_repository import ExternalSourceRepository
from app.services.catalog_import_profiles import (
    CatalogImportProfile,
    CatalogImportQuery,
)
from app.services.catalog_import_service import CatalogImportService
from app.services.external.base import BookSourceAdapter, ExternalBookDetail
from app.services.external.registry import _registry, register_adapter

_FAKE_SOURCE = "fake_catalog_source"


class FakeAdapter(BookSourceAdapter):
    name = _FAKE_SOURCE
    payloads_by_query: ClassVar[dict[str, list[dict[str, object]]]] = {}
    details_by_key: ClassVar[dict[str, ExternalBookDetail]] = {}

    async def search(
        self, query: str, session: AsyncSession
    ) -> list[ExternalSourceRecord]:
        repo = ExternalSourceRepository(session)
        return [
            await repo.create(
                source=self.name,
                ref_kind=ExternalRefKind.search,
                ref=query,
                payload=payload,
            )
            for payload in self.payloads_by_query.get(query, [])
        ]

    async def get_by_isbn(
        self, isbn: str, session: AsyncSession
    ) -> ExternalSourceRecord | None:
        return None

    async def get_detail(
        self, source_id: str, session: AsyncSession
    ) -> ExternalBookDetail | None:
        return self.details_by_key.get(source_id)


@pytest.fixture(autouse=True)
def _register_fake_adapter():
    register_adapter(_FAKE_SOURCE)(FakeAdapter)
    yield
    _registry.pop(_FAKE_SOURCE, None)
    FakeAdapter.payloads_by_query = {}
    FakeAdapter.details_by_key = {}


def _detail(title: str) -> ExternalBookDetail:
    return ExternalBookDetail(
        title=title,
        description="desc",
        contributors=[],
        isbns=[],
        format=ReleaseFormat.paperback,
        publisher="Pub",
        published_year=2020,
        language="en",
    )


class TestRunProfile:
    async def test_imports_hits_from_a_single_query(self, db_session: AsyncSession):
        FakeAdapter.payloads_by_query = {
            "subject:Fiction": [
                {
                    "key": "book-1",
                    "title": "Book One",
                    "isbn_13": [],
                    "author_name": [],
                },
                {
                    "key": "book-2",
                    "title": "Book Two",
                    "isbn_13": [],
                    "author_name": [],
                },
            ]
        }
        FakeAdapter.details_by_key = {
            "book-1": _detail("Book One"),
            "book-2": _detail("Book Two"),
        }
        profile = CatalogImportProfile(
            name="test",
            target_count=1,
            queries=[
                CatalogImportQuery(text="subject:Fiction", sources=[_FAKE_SOURCE])
            ],
        )
        service = CatalogImportService(db_session)

        summary = await service.run_profile(profile)

        assert summary.profile == "test"
        assert summary.target_count == 1
        assert summary.attempted == 2
        assert summary.imported == 2
        assert summary.failed == 0

    async def test_stops_once_target_reached_across_queries(
        self, db_session: AsyncSession
    ):
        FakeAdapter.payloads_by_query = {
            "subject:Fiction": [
                {
                    "key": "book-1",
                    "title": "Book One",
                    "isbn_13": [],
                    "author_name": [],
                },
            ],
            "subject:Fantasy": [
                {
                    "key": "book-2",
                    "title": "Book Two",
                    "isbn_13": [],
                    "author_name": [],
                },
            ],
        }
        FakeAdapter.details_by_key = {
            "book-1": _detail("Book One"),
            "book-2": _detail("Book Two"),
        }
        profile = CatalogImportProfile(
            name="test",
            target_count=1,
            queries=[
                CatalogImportQuery(text="subject:Fiction", sources=[_FAKE_SOURCE]),
                CatalogImportQuery(text="subject:Fantasy", sources=[_FAKE_SOURCE]),
            ],
        )
        service = CatalogImportService(db_session)

        summary = await service.run_profile(profile)

        assert summary.attempted == 1
        assert summary.imported == 1
        assert summary.failed == 0

    async def test_counts_import_failures_without_raising(
        self, db_session: AsyncSession
    ):
        FakeAdapter.payloads_by_query = {
            "subject:Fiction": [
                {
                    "key": "no-detail",
                    "title": "Ghost Book",
                    "isbn_13": [],
                    "author_name": [],
                },
            ]
        }
        FakeAdapter.details_by_key = {}
        profile = CatalogImportProfile(
            name="test",
            target_count=5,
            queries=[
                CatalogImportQuery(text="subject:Fiction", sources=[_FAKE_SOURCE])
            ],
        )
        service = CatalogImportService(db_session)

        summary = await service.run_profile(profile)

        assert summary.attempted == 1
        assert summary.failed == 1
        assert summary.imported == 0

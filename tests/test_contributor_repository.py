import pytest
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col, delete

from app.core.db import get_session
from app.models.catalog import Contributor
from app.repositories.contributor_repository import ContributorRepository, slugify


@pytest.fixture
async def session():
    async for session in get_session():
        yield session


@pytest.fixture
async def cleanup_contributors():
    created_ids: list = []
    yield created_ids
    try:
        async for session in get_session():
            if created_ids:
                await session.execute(
                    delete(Contributor).where(col(Contributor.id).in_(created_ids))
                )
                await session.commit()
    except (SQLAlchemyError, OSError) as exc:
        pytest.skip(f"database unavailable: {exc}")


class TestSlugify:
    def test_lowercases_and_hyphenates(self):
        assert slugify("Frank Herbert") == "frank-herbert"

    def test_strips_invalid_chars(self):
        assert slugify("O'Brien, Jr.") == "o-brien-jr"

    def test_falls_back_to_contributor_when_empty(self):
        assert slugify("###") == "contributor"


class TestGetByName:
    async def test_returns_none_when_missing(self, session: AsyncSession):
        repo = ContributorRepository(session)
        result = await repo.get_by_name("Nobody Special", "Special, Nobody")
        assert result is None


class TestAdd:
    async def test_creates_contributor_with_slug(
        self, session: AsyncSession, cleanup_contributors: list
    ):
        repo = ContributorRepository(session)
        contributor = await repo.add(
            "Test Contributor Alpha", "Alpha, Test Contributor"
        )
        await session.commit()
        cleanup_contributors.append(contributor.id)

        assert contributor.id is not None
        assert contributor.slug == "test-contributor-alpha"
        assert contributor.full_name == "Test Contributor Alpha"
        assert contributor.sort_name == "Alpha, Test Contributor"

    async def test_generates_unique_slug_on_collision(
        self, session: AsyncSession, cleanup_contributors: list
    ):
        repo = ContributorRepository(session)
        first = await repo.add("Test Contributor Beta", "Beta, Test Contributor")
        second = await repo.add("Test Contributor Beta", "Beta, Test Contributor Two")
        await session.commit()
        cleanup_contributors.extend([first.id, second.id])

        assert first.slug == "test-contributor-beta"
        assert second.slug == "test-contributor-beta-2"

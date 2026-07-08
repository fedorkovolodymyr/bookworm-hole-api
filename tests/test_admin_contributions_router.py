import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.main import app
from app.models.contribution import Contribution, ContributionKind, ContributionStatus
from app.models.user import User
from app.repositories.contribution_repository import ContributionRepository


def _login_as(user: User) -> None:
    app.dependency_overrides[get_current_user] = lambda: user


@pytest.fixture
async def admin_user(db_session: AsyncSession) -> User:
    user = User(
        email="admin@test.com",
        username="admin",
        display_name="Admin",
        is_admin=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    _login_as(user)
    yield user
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
async def regular_user(db_session: AsyncSession) -> User:
    user = User(
        email="user@test.com",
        username="user",
        display_name="Regular User",
        is_admin=False,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def contribution(db_session: AsyncSession, regular_user: User) -> Contribution:
    repo = ContributionRepository(db_session)
    contrib = Contribution(
        user_id=regular_user.id,
        kind=ContributionKind.new_book,
        target_id=None,
        payload={"title": "Test Book", "author": "Test Author"},
        status=ContributionStatus.submitted,
    )
    return await repo.create(contrib)


class TestAdminContributionsQueue:
    async def test_list_submitted_contributions(
        self,
        async_client: AsyncClient,
        admin_user: User,
        contribution: Contribution,
    ):
        response = await async_client.get(
            "/api/v1/admin/contributions/?status=submitted"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
        assert len(data["items"]) >= 1
        assert any(item["id"] == str(contribution.id) for item in data["items"])

    async def test_list_submitted_as_non_admin(
        self,
        async_client: AsyncClient,
        regular_user: User,
    ):
        _login_as(regular_user)
        try:
            response = await async_client.get(
                "/api/v1/admin/contributions/?status=submitted"
            )
        finally:
            app.dependency_overrides.pop(get_current_user, None)
        assert response.status_code == 403

    async def test_claim_contribution(
        self,
        async_client: AsyncClient,
        admin_user: User,
        contribution: Contribution,
    ):
        response = await async_client.post(
            f"/api/v1/admin/contributions/{contribution.id}/claim"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "under_review"
        assert data["reviewer_id"] == str(admin_user.id)

    async def test_reject_contribution(
        self,
        async_client: AsyncClient,
        admin_user: User,
        db_session: AsyncSession,
    ):
        repo = ContributionRepository(db_session)
        contrib = Contribution(
            user_id=admin_user.id,
            kind=ContributionKind.new_book,
            target_id=None,
            payload={"title": "Test"},
            status=ContributionStatus.under_review,
            reviewer_id=admin_user.id,
        )
        contrib = await repo.create(contrib)

        response = await async_client.post(
            f"/api/v1/admin/contributions/{contrib.id}/reject",
            json={"notes": "Does not meet requirements"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "rejected"
        assert data["review_notes"] == "Does not meet requirements"

    async def test_approve_contribution(
        self,
        async_client: AsyncClient,
        admin_user: User,
        db_session: AsyncSession,
    ):
        repo = ContributionRepository(db_session)
        contrib = Contribution(
            user_id=admin_user.id,
            kind=ContributionKind.new_book,
            target_id=None,
            payload={"title": "Test"},
            status=ContributionStatus.under_review,
            reviewer_id=admin_user.id,
        )
        contrib = await repo.create(contrib)

        response = await async_client.post(
            f"/api/v1/admin/contributions/{contrib.id}/approve"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "merged"

    async def test_get_diff(
        self,
        async_client: AsyncClient,
        admin_user: User,
        contribution: Contribution,
    ):
        response = await async_client.get(
            f"/api/v1/admin/contributions/{contribution.id}/diff"
        )
        assert response.status_code == 200
        data = response.json()
        assert "proposed" in data
        assert "current" in data
        assert data["proposed"] == {"title": "Test Book", "author": "Test Author"}
        assert data["current"] is None

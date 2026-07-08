import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.models.contribution import Contribution, ContributionKind, ContributionStatus
from app.models.user import User
from app.repositories.contribution_repository import ContributionRepository
from app.services.user_service import UserService


@pytest.fixture
async def admin_user(session: AsyncSession) -> User:
    from app.repositories.collection_repository import CollectionRepository
    from app.repositories.password_reset_token_repository import (
        PasswordResetTokenRepository,
    )
    from app.repositories.user_repository import UserRepository

    user_repo = UserRepository(session)
    service = UserService(
        user_repo,
        CollectionRepository(session),
        PasswordResetTokenRepository(session),
    )
    user = await service.create_user(
        email="admin@test.com",
        username="admin",
        password="Test1234!",
    )
    await service.promote_user(user.id)
    return user


@pytest.fixture
async def regular_user(session: AsyncSession) -> User:
    from app.repositories.collection_repository import CollectionRepository
    from app.repositories.password_reset_token_repository import (
        PasswordResetTokenRepository,
    )
    from app.repositories.user_repository import UserRepository

    user_repo = UserRepository(session)
    service = UserService(
        user_repo,
        CollectionRepository(session),
        PasswordResetTokenRepository(session),
    )
    return await service.create_user(
        email="user@test.com",
        username="user",
        password="Test1234!",
    )


@pytest.fixture
async def contribution(session: AsyncSession, regular_user: User) -> Contribution:
    repo = ContributionRepository(session)
    contrib = Contribution(
        user_id=regular_user.id,
        kind=ContributionKind.new_book,
        target_id=None,
        payload={"title": "Test Book", "author": "Test Author"},
        status=ContributionStatus.submitted,
    )
    return await repo.create(contrib)


@pytest.fixture
async def client() -> AsyncClient:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac


class TestAdminContributionsQueue:
    async def test_list_submitted_contributions(
        self,
        client: AsyncClient,
        admin_user: User,
        contribution: Contribution,
    ):
        app.dependency_overrides.clear()
        from app.core.deps import get_current_user

        async def override_get_current_user():
            return admin_user

        app.dependency_overrides[get_current_user] = override_get_current_user

        response = await client.get("/api/v1/admin/contributions?status=submitted")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
        assert len(data["items"]) >= 1
        assert any(item["id"] == str(contribution.id) for item in data["items"])

        app.dependency_overrides.clear()

    async def test_list_submitted_as_non_admin(
        self,
        client: AsyncClient,
        regular_user: User,
    ):
        app.dependency_overrides.clear()
        from app.core.deps import get_current_user

        async def override_get_current_user():
            return regular_user

        app.dependency_overrides[get_current_user] = override_get_current_user

        response = await client.get("/api/v1/admin/contributions?status=submitted")
        assert response.status_code == 403

        app.dependency_overrides.clear()

    async def test_claim_contribution(
        self,
        client: AsyncClient,
        admin_user: User,
        contribution: Contribution,
    ):
        app.dependency_overrides.clear()
        from app.core.deps import get_current_user

        async def override_get_current_user():
            return admin_user

        app.dependency_overrides[get_current_user] = override_get_current_user

        response = await client.post(
            f"/api/v1/admin/contributions/{contribution.id}/claim"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "under_review"
        assert data["reviewer_id"] == str(admin_user.id)

        app.dependency_overrides.clear()

    async def test_reject_contribution(
        self,
        client: AsyncClient,
        admin_user: User,
        session: AsyncSession,
    ):
        app.dependency_overrides.clear()
        from app.core.deps import get_current_user

        repo = ContributionRepository(session)
        contrib = Contribution(
            user_id=admin_user.id,
            kind=ContributionKind.new_book,
            target_id=None,
            payload={"title": "Test"},
            status=ContributionStatus.under_review,
            reviewer_id=admin_user.id,
        )
        contrib = await repo.create(contrib)

        async def override_get_current_user():
            return admin_user

        app.dependency_overrides[get_current_user] = override_get_current_user

        response = await client.post(
            f"/api/v1/admin/contributions/{contrib.id}/reject",
            json={"notes": "Does not meet requirements"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "rejected"
        assert data["review_notes"] == "Does not meet requirements"

        app.dependency_overrides.clear()

    async def test_approve_contribution(
        self,
        client: AsyncClient,
        admin_user: User,
        session: AsyncSession,
    ):
        app.dependency_overrides.clear()
        from app.core.deps import get_current_user

        repo = ContributionRepository(session)
        contrib = Contribution(
            user_id=admin_user.id,
            kind=ContributionKind.new_book,
            target_id=None,
            payload={"title": "Test"},
            status=ContributionStatus.under_review,
            reviewer_id=admin_user.id,
        )
        contrib = await repo.create(contrib)

        async def override_get_current_user():
            return admin_user

        app.dependency_overrides[get_current_user] = override_get_current_user

        response = await client.post(
            f"/api/v1/admin/contributions/{contrib.id}/approve"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "merged"

        app.dependency_overrides.clear()

    async def test_get_diff(
        self,
        client: AsyncClient,
        admin_user: User,
        contribution: Contribution,
    ):
        app.dependency_overrides.clear()
        from app.core.deps import get_current_user

        async def override_get_current_user():
            return admin_user

        app.dependency_overrides[get_current_user] = override_get_current_user

        response = await client.get(
            f"/api/v1/admin/contributions/{contribution.id}/diff"
        )
        assert response.status_code == 200
        data = response.json()
        assert "proposed" in data
        assert "current" in data
        assert data["proposed"] == {"title": "Test Book", "author": "Test Author"}
        assert data["current"] is None

        app.dependency_overrides.clear()

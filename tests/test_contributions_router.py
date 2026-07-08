from collections.abc import AsyncIterator

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.main import app
from app.models.contribution import Contribution, ContributionKind, ContributionStatus
from app.models.user import User


def _login_as(user: User) -> None:
    app.dependency_overrides[get_current_user] = lambda: user


@pytest.fixture
async def user(db_session: AsyncSession) -> AsyncIterator[User]:
    user = User(email="test@example.com", username="testuser", display_name="Test User")
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    _login_as(user)
    yield user
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
async def other_user(db_session: AsyncSession) -> User:
    user = User(
        email="other@example.com", username="otheruser", display_name="Other User"
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


class TestCreateContribution:
    async def test_create_contribution_success(
        self, async_client: AsyncClient, user: User
    ):
        response = await async_client.post(
            "/api/v1/contributions/",
            json={
                "kind": "new_book",
                "target_id": None,
                "payload": {"title": "Test Book", "author": "Test Author"},
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["kind"] == "new_book"
        assert data["status"] == "draft"
        assert data["payload"]["title"] == "Test Book"
        assert data["user_id"] == str(user.id)

    async def test_create_contribution_requires_auth(self, async_client: AsyncClient):
        app.dependency_overrides.pop(get_current_user, None)

        response = await async_client.post(
            "/api/v1/contributions/",
            json={
                "kind": "new_book",
                "target_id": None,
                "payload": {"title": "Test Book"},
            },
        )

        assert response.status_code == 401


class TestGetContribution:
    async def test_get_own_contribution(
        self, async_client: AsyncClient, db_session: AsyncSession, user: User
    ):
        contribution = Contribution(
            user_id=user.id,
            kind=ContributionKind.new_book,
            payload={"title": "Test"},
            status=ContributionStatus.draft,
        )
        db_session.add(contribution)
        await db_session.commit()
        await db_session.refresh(contribution)

        response = await async_client.get(f"/api/v1/contributions/{contribution.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(contribution.id)
        assert data["status"] == "draft"

    async def test_get_others_contribution_forbidden(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        user: User,
        other_user: User,
    ):
        contribution = Contribution(
            user_id=other_user.id,
            kind=ContributionKind.new_book,
            payload={"title": "Test"},
            status=ContributionStatus.draft,
        )
        db_session.add(contribution)
        await db_session.commit()
        await db_session.refresh(contribution)

        response = await async_client.get(f"/api/v1/contributions/{contribution.id}")

        assert response.status_code == 404


class TestUpdateContribution:
    async def test_update_draft_contribution(
        self, async_client: AsyncClient, db_session: AsyncSession, user: User
    ):
        contribution = Contribution(
            user_id=user.id,
            kind=ContributionKind.new_book,
            payload={"title": "Old Title"},
            status=ContributionStatus.draft,
        )
        db_session.add(contribution)
        await db_session.commit()
        await db_session.refresh(contribution)

        response = await async_client.patch(
            f"/api/v1/contributions/{contribution.id}",
            json={"payload": {"title": "New Title"}},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["payload"]["title"] == "New Title"

    async def test_cannot_update_submitted_contribution(
        self, async_client: AsyncClient, db_session: AsyncSession, user: User
    ):
        contribution = Contribution(
            user_id=user.id,
            kind=ContributionKind.new_book,
            payload={"title": "Test"},
            status=ContributionStatus.submitted,
        )
        db_session.add(contribution)
        await db_session.commit()
        await db_session.refresh(contribution)

        response = await async_client.patch(
            f"/api/v1/contributions/{contribution.id}",
            json={"payload": {"title": "New"}},
        )

        assert response.status_code == 409


class TestSubmitContribution:
    async def test_submit_draft_contribution(
        self, async_client: AsyncClient, db_session: AsyncSession, user: User
    ):
        contribution = Contribution(
            user_id=user.id,
            kind=ContributionKind.new_book,
            payload={"title": "Test"},
            status=ContributionStatus.draft,
        )
        db_session.add(contribution)
        await db_session.commit()
        await db_session.refresh(contribution)

        response = await async_client.post(
            f"/api/v1/contributions/{contribution.id}/submit"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "submitted"

    async def test_cannot_submit_already_submitted(
        self, async_client: AsyncClient, db_session: AsyncSession, user: User
    ):
        contribution = Contribution(
            user_id=user.id,
            kind=ContributionKind.new_book,
            payload={"title": "Test"},
            status=ContributionStatus.submitted,
        )
        db_session.add(contribution)
        await db_session.commit()
        await db_session.refresh(contribution)

        response = await async_client.post(
            f"/api/v1/contributions/{contribution.id}/submit"
        )

        assert response.status_code == 409


class TestDeleteContribution:
    async def test_delete_draft_contribution(
        self, async_client: AsyncClient, db_session: AsyncSession, user: User
    ):
        contribution = Contribution(
            user_id=user.id,
            kind=ContributionKind.new_book,
            payload={"title": "Test"},
            status=ContributionStatus.draft,
        )
        db_session.add(contribution)
        await db_session.commit()
        await db_session.refresh(contribution)

        response = await async_client.delete(f"/api/v1/contributions/{contribution.id}")

        assert response.status_code == 204

    async def test_delete_submitted_contribution(
        self, async_client: AsyncClient, db_session: AsyncSession, user: User
    ):
        contribution = Contribution(
            user_id=user.id,
            kind=ContributionKind.new_book,
            payload={"title": "Test"},
            status=ContributionStatus.submitted,
        )
        db_session.add(contribution)
        await db_session.commit()
        await db_session.refresh(contribution)

        response = await async_client.delete(f"/api/v1/contributions/{contribution.id}")

        assert response.status_code == 204

    async def test_cannot_delete_under_review(
        self, async_client: AsyncClient, db_session: AsyncSession, user: User
    ):
        contribution = Contribution(
            user_id=user.id,
            kind=ContributionKind.new_book,
            payload={"title": "Test"},
            status=ContributionStatus.under_review,
        )
        db_session.add(contribution)
        await db_session.commit()
        await db_session.refresh(contribution)

        response = await async_client.delete(f"/api/v1/contributions/{contribution.id}")

        assert response.status_code == 409


class TestListOwnContributions:
    async def test_list_own_contributions_success(
        self, async_client: AsyncClient, db_session: AsyncSession, user: User
    ):
        for i in range(3):
            contribution = Contribution(
                user_id=user.id,
                kind=ContributionKind.new_book,
                payload={"index": i},
                status=ContributionStatus.draft,
            )
            db_session.add(contribution)
        await db_session.commit()

        response = await async_client.get("/api/v1/contributions/me/contributions")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3
        assert len(data["items"]) == 3

    async def test_list_own_contributions_pagination(
        self, async_client: AsyncClient, db_session: AsyncSession, user: User
    ):
        for i in range(15):
            contribution = Contribution(
                user_id=user.id,
                kind=ContributionKind.new_book,
                payload={"index": i},
                status=ContributionStatus.draft,
            )
            db_session.add(contribution)
        await db_session.commit()

        response = await async_client.get(
            "/api/v1/contributions/me/contributions?skip=0&limit=5"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 15
        assert len(data["items"]) == 5

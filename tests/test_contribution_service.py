from collections.abc import AsyncIterator

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ConflictError, ErrorMessages, NotFoundError
from app.models.contribution import Contribution, ContributionKind, ContributionStatus
from app.models.user import User
from app.repositories.contribution_repository import ContributionRepository
from app.schemas.contribution_schemas import (
    CreateContributionSchema,
    UpdateContributionSchema,
)
from app.services.contribution_service import ContributionService


@pytest.fixture
async def user(db_session: AsyncSession) -> AsyncIterator[User]:
    user = User(email="test@example.com", username="testuser", display_name="Test User")
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    yield user


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
    async def test_create_draft_contribution(self, db_session, user):
        repository = ContributionRepository(db_session)
        service = ContributionService(repository)

        schema = CreateContributionSchema(
            kind=ContributionKind.new_book,
            target_id=None,
            payload={"title": "Test Book"},
        )

        result = await service.create_contribution(user.id, schema)

        assert result.user_id == user.id
        assert result.kind == ContributionKind.new_book
        assert result.status == ContributionStatus.draft
        assert result.payload == {"title": "Test Book"}
        assert result.id is not None


class TestUpdateContribution:
    async def test_update_draft_contribution(self, db_session, user):
        repository = ContributionRepository(db_session)
        service = ContributionService(repository)

        contribution = Contribution(
            user_id=user.id,
            kind=ContributionKind.new_book,
            payload={"title": "Old Title"},
            status=ContributionStatus.draft,
        )
        created = await repository.create(contribution)

        update_schema = UpdateContributionSchema(payload={"title": "New Title"})
        result = await service.update_contribution(user.id, created.id, update_schema)

        assert result.payload == {"title": "New Title"}
        assert result.status == ContributionStatus.draft

    async def test_cannot_update_submitted_contribution(self, db_session, user):
        repository = ContributionRepository(db_session)
        service = ContributionService(repository)

        contribution = Contribution(
            user_id=user.id,
            kind=ContributionKind.new_book,
            payload={"title": "Test"},
            status=ContributionStatus.submitted,
        )
        created = await repository.create(contribution)

        update_schema = UpdateContributionSchema(payload={"title": "New"})

        with pytest.raises(ConflictError, match=ErrorMessages.CONTRIBUTION_NOT_DRAFT):
            await service.update_contribution(user.id, created.id, update_schema)

    async def test_cannot_update_others_contribution(
        self, db_session, user, other_user
    ):
        repository = ContributionRepository(db_session)
        service = ContributionService(repository)

        contribution = Contribution(
            user_id=other_user.id,
            kind=ContributionKind.new_book,
            payload={"title": "Test"},
            status=ContributionStatus.draft,
        )
        created = await repository.create(contribution)

        update_schema = UpdateContributionSchema(payload={"title": "New"})

        with pytest.raises(NotFoundError, match=ErrorMessages.CONTRIBUTION_NOT_FOUND):
            await service.update_contribution(user.id, created.id, update_schema)


class TestSubmitContribution:
    async def test_submit_draft_contribution(self, db_session, user):
        repository = ContributionRepository(db_session)
        service = ContributionService(repository)

        contribution = Contribution(
            user_id=user.id,
            kind=ContributionKind.new_book,
            payload={"title": "Test"},
            status=ContributionStatus.draft,
        )
        created = await repository.create(contribution)

        result = await service.submit_contribution(user.id, created.id)

        assert result.status == ContributionStatus.submitted
        assert result.id == created.id

    async def test_cannot_submit_already_submitted(self, db_session, user):
        repository = ContributionRepository(db_session)
        service = ContributionService(repository)

        contribution = Contribution(
            user_id=user.id,
            kind=ContributionKind.new_book,
            payload={"title": "Test"},
            status=ContributionStatus.submitted,
        )
        created = await repository.create(contribution)

        with pytest.raises(ConflictError, match=ErrorMessages.CONTRIBUTION_NOT_DRAFT):
            await service.submit_contribution(user.id, created.id)

    async def test_cannot_submit_others_contribution(
        self, db_session, user, other_user
    ):
        repository = ContributionRepository(db_session)
        service = ContributionService(repository)

        contribution = Contribution(
            user_id=other_user.id,
            kind=ContributionKind.new_book,
            payload={"title": "Test"},
            status=ContributionStatus.draft,
        )
        created = await repository.create(contribution)

        with pytest.raises(NotFoundError, match=ErrorMessages.CONTRIBUTION_NOT_FOUND):
            await service.submit_contribution(user.id, created.id)


class TestDeleteContribution:
    async def test_delete_draft_contribution(self, db_session, user):
        repository = ContributionRepository(db_session)
        service = ContributionService(repository)

        contribution = Contribution(
            user_id=user.id,
            kind=ContributionKind.new_book,
            payload={"title": "Test"},
            status=ContributionStatus.draft,
        )
        created = await repository.create(contribution)

        await service.delete_contribution(user.id, created.id)

        deleted = await repository.get_by_id(created.id)
        assert deleted is None

    async def test_delete_submitted_contribution(self, db_session, user):
        repository = ContributionRepository(db_session)
        service = ContributionService(repository)

        contribution = Contribution(
            user_id=user.id,
            kind=ContributionKind.new_book,
            payload={"title": "Test"},
            status=ContributionStatus.submitted,
        )
        created = await repository.create(contribution)

        await service.delete_contribution(user.id, created.id)

        deleted = await repository.get_by_id(created.id)
        assert deleted is None

    async def test_cannot_delete_under_review(self, db_session, user):
        repository = ContributionRepository(db_session)
        service = ContributionService(repository)

        contribution = Contribution(
            user_id=user.id,
            kind=ContributionKind.new_book,
            payload={"title": "Test"},
            status=ContributionStatus.under_review,
        )
        created = await repository.create(contribution)

        with pytest.raises(
            ConflictError, match=ErrorMessages.CONTRIBUTION_CANNOT_DELETE
        ):
            await service.delete_contribution(user.id, created.id)

    async def test_cannot_delete_others_contribution(
        self, db_session, user, other_user
    ):
        repository = ContributionRepository(db_session)
        service = ContributionService(repository)

        contribution = Contribution(
            user_id=other_user.id,
            kind=ContributionKind.new_book,
            payload={"title": "Test"},
            status=ContributionStatus.draft,
        )
        created = await repository.create(contribution)

        with pytest.raises(NotFoundError, match=ErrorMessages.CONTRIBUTION_NOT_FOUND):
            await service.delete_contribution(user.id, created.id)


class TestListOwnContributions:
    async def test_list_own_contributions(self, db_session, user, other_user):
        repository = ContributionRepository(db_session)
        service = ContributionService(repository)

        for i in range(3):
            await repository.create(
                Contribution(
                    user_id=user.id,
                    kind=ContributionKind.new_book,
                    payload={"index": i},
                    status=ContributionStatus.draft,
                )
            )

        await repository.create(
            Contribution(
                user_id=other_user.id,
                kind=ContributionKind.new_book,
                payload={"index": 99},
                status=ContributionStatus.draft,
            )
        )

        result = await service.list_own(user.id)

        assert result.total == 3
        assert len(result.items) == 3
        assert all(item.user_id == user.id for item in result.items)

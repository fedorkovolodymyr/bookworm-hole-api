from uuid import UUID

from app.core.errors import ConflictError, ErrorMessages, NotFoundError
from app.models.contribution import Contribution, ContributionStatus
from app.repositories.contribution_repository import ContributionRepository
from app.schemas.common_schemas import Page
from app.schemas.contribution_schemas import (
    ContributionDiffResponse,
    CreateContributionSchema,
    UpdateContributionSchema,
)


class ContributionService:
    def __init__(self, repository: ContributionRepository):
        self.repository = repository

    async def _get_owned(self, user_id: UUID, contribution_id: UUID) -> Contribution:
        contribution = await self.repository.get_by_id(contribution_id)
        if not contribution or contribution.user_id != user_id:
            raise NotFoundError(ErrorMessages.CONTRIBUTION_NOT_FOUND)
        return contribution

    def _check_draft_only(self, contribution: Contribution) -> None:
        if contribution.status != ContributionStatus.draft:
            raise ConflictError(ErrorMessages.CONTRIBUTION_NOT_DRAFT)

    def _check_draft_or_submitted(self, contribution: Contribution) -> None:
        if contribution.status not in (
            ContributionStatus.draft,
            ContributionStatus.submitted,
        ):
            raise ConflictError(ErrorMessages.CONTRIBUTION_CANNOT_DELETE)

    async def create_contribution(
        self, user_id: UUID, data: CreateContributionSchema
    ) -> Contribution:
        contribution = Contribution(
            user_id=user_id,
            kind=data.kind,
            target_id=data.target_id,
            payload=data.payload,
            status=ContributionStatus.draft,
        )
        return await self.repository.create(contribution)

    async def get_contribution(
        self, user_id: UUID, contribution_id: UUID
    ) -> Contribution:
        return await self._get_owned(user_id, contribution_id)

    async def update_contribution(
        self, user_id: UUID, contribution_id: UUID, data: UpdateContributionSchema
    ) -> Contribution:
        contribution = await self._get_owned(user_id, contribution_id)
        self._check_draft_only(contribution)
        updated = await self.repository.update(contribution_id, data)
        if not updated:
            raise NotFoundError(ErrorMessages.CONTRIBUTION_NOT_FOUND)
        return updated

    async def submit_contribution(
        self, user_id: UUID, contribution_id: UUID
    ) -> Contribution:
        contribution = await self._get_owned(user_id, contribution_id)
        self._check_draft_only(contribution)
        updated = await self.repository.update_status(
            contribution_id, ContributionStatus.submitted
        )
        if not updated:
            raise NotFoundError(ErrorMessages.CONTRIBUTION_NOT_FOUND)
        return updated

    async def delete_contribution(self, user_id: UUID, contribution_id: UUID) -> None:
        contribution = await self._get_owned(user_id, contribution_id)
        self._check_draft_or_submitted(contribution)
        deleted = await self.repository.delete(contribution_id)
        if not deleted:
            raise NotFoundError(ErrorMessages.CONTRIBUTION_NOT_FOUND)

    async def list_own(
        self, user_id: UUID, skip: int = 0, limit: int = 10
    ) -> Page[Contribution]:
        items, total = await self.repository.list_by_user(user_id, skip, limit)
        return Page(items=list(items), total=total, limit=limit, offset=skip)

    async def list_by_status(
        self, status: ContributionStatus, skip: int = 0, limit: int = 10
    ) -> Page[Contribution]:
        items, total = await self.repository.list_by_status(status, skip, limit)
        return Page(items=list(items), total=total, limit=limit, offset=skip)

    async def claim_contribution(
        self, contribution_id: UUID, reviewer_id: UUID
    ) -> Contribution:
        contribution = await self.repository.get_by_id(contribution_id)
        if not contribution:
            raise NotFoundError(ErrorMessages.CONTRIBUTION_NOT_FOUND)
        if contribution.status != ContributionStatus.submitted:
            raise ConflictError(ErrorMessages.CONTRIBUTION_NOT_SUBMITTED)
        updated = await self.repository.update_reviewer(contribution_id, reviewer_id)
        if not updated:
            raise NotFoundError(ErrorMessages.CONTRIBUTION_NOT_FOUND)
        updated = await self.repository.update_status(
            contribution_id, ContributionStatus.under_review
        )
        if not updated:
            raise NotFoundError(ErrorMessages.CONTRIBUTION_NOT_FOUND)
        return updated

    async def reject_contribution(
        self, contribution_id: UUID, notes: str
    ) -> Contribution:
        contribution = await self.repository.get_by_id(contribution_id)
        if not contribution:
            raise NotFoundError(ErrorMessages.CONTRIBUTION_NOT_FOUND)
        if contribution.status != ContributionStatus.under_review:
            raise ConflictError(ErrorMessages.CONTRIBUTION_NOT_UNDER_REVIEW)
        updated = await self.repository.update_review_notes(contribution_id, notes)
        if not updated:
            raise NotFoundError(ErrorMessages.CONTRIBUTION_NOT_FOUND)
        updated = await self.repository.update_status(
            contribution_id, ContributionStatus.rejected
        )
        if not updated:
            raise NotFoundError(ErrorMessages.CONTRIBUTION_NOT_FOUND)
        return updated

    async def approve_contribution(self, contribution_id: UUID) -> Contribution:
        contribution = await self.repository.get_by_id(contribution_id)
        if not contribution:
            raise NotFoundError(ErrorMessages.CONTRIBUTION_NOT_FOUND)
        if contribution.status != ContributionStatus.under_review:
            raise ConflictError(ErrorMessages.CONTRIBUTION_NOT_UNDER_REVIEW)
        updated = await self.repository.update_status(
            contribution_id, ContributionStatus.merged
        )
        if not updated:
            raise NotFoundError(ErrorMessages.CONTRIBUTION_NOT_FOUND)
        return updated

    async def get_diff(self, contribution_id: UUID) -> ContributionDiffResponse:
        contribution = await self.repository.get_by_id(contribution_id)
        if not contribution:
            raise NotFoundError(ErrorMessages.CONTRIBUTION_NOT_FOUND)
        return ContributionDiffResponse(
            proposed=contribution.payload,
            current=None,
        )

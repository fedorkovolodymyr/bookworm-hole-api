from uuid import UUID

from fastapi import HTTPException

from app.core.errors import ErrorMessages, NotFoundError
from app.models.catalog import Contributor, ContributorRole, Release
from app.repositories.book_repository import BookRepository
from app.repositories.release_repository import ReleaseRepository
from app.repositories.review_repository import ReviewRepository
from app.schemas.book_schemas import (
    CreateReleaseSchema,
    ReleaseWithISBNsResponse,
    UpdateReleaseSchema,
)


class ReleaseService:
    def __init__(
        self,
        repository: ReleaseRepository,
        book_repository: BookRepository,
        review_repository: ReviewRepository,
    ) -> None:
        self.repository = repository
        self.book_repository = book_repository
        self.review_repository = review_repository

    async def create_release(self, new_release: CreateReleaseSchema) -> Release:
        book = await self.book_repository.get_by_id(new_release.book_id)
        if not book:
            raise HTTPException(status_code=404, detail="Book not found")
        release = Release(**new_release.model_dump())
        created = await self.repository.create(release)
        reloaded = await self.repository.get_by_id(created.id)
        if reloaded is None:
            raise HTTPException(status_code=500, detail="Failed to create release")
        return reloaded

    async def retrieve_release_by_id(
        self, release_id: UUID
    ) -> ReleaseWithISBNsResponse:
        release = await self.repository.get_by_id(release_id)
        if not release:
            raise HTTPException(status_code=404, detail="Release not found")

        (
            avg_rating,
            rating_count,
        ) = await self.review_repository.get_rating_aggregate_for_release(release_id)

        return ReleaseWithISBNsResponse.model_validate(release).model_copy(
            update={"average_rating": avg_rating, "rating_count": rating_count}
        )

    async def modify_release(
        self, release_id: UUID, updated_release: UpdateReleaseSchema
    ) -> Release:
        release = await self.repository.update(release_id, updated_release)
        if not release:
            raise HTTPException(status_code=404, detail="Release not found")
        return release

    async def add_contributor(
        self, release_id: UUID, contributor_id: UUID, role: ContributorRole
    ) -> bool:
        release = await self.repository.get_by_id(release_id)
        if not release:
            raise NotFoundError(ErrorMessages.RELEASE_NOT_FOUND)

        from app.repositories.contributor_repository import ContributorRepository

        contributor_repo = ContributorRepository(self.repository.session)
        contributor = await contributor_repo.get_by_id(contributor_id)
        if not contributor:
            raise NotFoundError(ErrorMessages.CONTRIBUTOR_NOT_FOUND)

        return await self.repository.add_contributor(release_id, contributor_id, role)

    async def remove_contributor(
        self, release_id: UUID, contributor_id: UUID, role: ContributorRole
    ) -> None:
        release = await self.repository.get_by_id(release_id)
        if not release:
            raise NotFoundError(ErrorMessages.RELEASE_NOT_FOUND)

        contributor = await self.repository.session.get(Contributor, contributor_id)
        if not contributor:
            raise NotFoundError(ErrorMessages.CONTRIBUTOR_NOT_FOUND)

        removed = await self.repository.remove_contributor(
            release_id, contributor_id, role
        )
        if not removed:
            raise NotFoundError("Contributor not attached to this release")

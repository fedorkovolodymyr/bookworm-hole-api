from collections import defaultdict
from uuid import UUID

from app.core.errors import ErrorMessages, NotFoundError
from app.models.catalog import Book, Contributor, ContributorRole
from app.repositories.contributor_repository import ContributorRepository
from app.schemas.common_schemas import Page
from app.schemas.contributor_schemas import (
    ContributorBookSummary,
    ContributorDetailResponse,
    ContributorReleaseSummary,
    CreateContributorSchema,
    UpdateContributorSchema,
)


class ContributorService:
    def __init__(self, repository: ContributorRepository):
        self.repository = repository

    async def create_contributor(self, data: CreateContributorSchema) -> Contributor:
        return await self.repository.create(
            data.full_name, data.sort_name, data.birth_year, data.death_year, data.bio
        )

    async def retrieve_all_contributors(
        self,
        skip: int = 0,
        limit: int = 10,
        name: str | None = None,
        role: ContributorRole | None = None,
    ) -> Page[Contributor]:
        items, total = await self.repository.get_all(skip, limit, name, role)
        return Page(items=list(items), total=total, limit=limit, offset=skip)

    async def retrieve_contributor_detail(
        self, contributor_id: UUID
    ) -> ContributorDetailResponse:
        contributor = await self.repository.get_by_id(contributor_id)
        if not contributor:
            raise NotFoundError(ErrorMessages.CONTRIBUTOR_NOT_FOUND)

        books_by_role: dict[ContributorRole, list[ContributorBookSummary]] = (
            defaultdict(list)
        )
        for book, role in await self.repository.get_books_by_role(contributor_id):
            books_by_role[role].append(ContributorBookSummary.model_validate(book))

        releases_by_role: dict[ContributorRole, list[ContributorReleaseSummary]] = (
            defaultdict(list)
        )
        for release, role in await self.repository.get_releases_by_role(contributor_id):
            releases_by_role[role].append(
                ContributorReleaseSummary.model_validate(release)
            )

        return ContributorDetailResponse(
            id=contributor.id,
            full_name=contributor.full_name,
            sort_name=contributor.sort_name,
            birth_year=contributor.birth_year,
            death_year=contributor.death_year,
            bio=contributor.bio,
            slug=contributor.slug,
            created_at=contributor.created_at,
            updated_at=contributor.updated_at,
            books_by_role=dict(books_by_role),
            releases_by_role=dict(releases_by_role),
        )

    async def retrieve_contributor_books(
        self, contributor_id: UUID, skip: int = 0, limit: int = 10
    ) -> Page[Book]:
        contributor = await self.repository.get_by_id(contributor_id)
        if not contributor:
            raise NotFoundError(ErrorMessages.CONTRIBUTOR_NOT_FOUND)
        items, total = await self.repository.get_books(contributor_id, skip, limit)
        return Page(items=list(items), total=total, limit=limit, offset=skip)

    async def modify_contributor(
        self, contributor_id: UUID, data: UpdateContributorSchema
    ) -> Contributor:
        contributor = await self.repository.update(contributor_id, data)
        if not contributor:
            raise NotFoundError(ErrorMessages.CONTRIBUTOR_NOT_FOUND)
        return contributor

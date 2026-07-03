from uuid import UUID

from fastapi import HTTPException

from app.models.catalog import Release
from app.repositories.book_repository import BookRepository
from app.repositories.release_repository import ReleaseRepository
from app.schemas.book_schemas import CreateReleaseSchema, UpdateReleaseSchema


class ReleaseService:
    def __init__(self, repository: ReleaseRepository, book_repository: BookRepository):
        self.repository = repository
        self.book_repository = book_repository

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

    async def retrieve_release_by_id(self, release_id: UUID) -> Release:
        release = await self.repository.get_by_id(release_id)
        if not release:
            raise HTTPException(status_code=404, detail="Release not found")
        return release

    async def modify_release(
        self, release_id: UUID, updated_release: UpdateReleaseSchema
    ) -> Release:
        release = await self.repository.update(
            release_id, updated_release.model_dump(exclude_unset=True)
        )
        if not release:
            raise HTTPException(status_code=404, detail="Release not found")
        return release

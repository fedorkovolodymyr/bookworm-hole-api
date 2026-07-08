from uuid import UUID

from app.core.errors import ErrorMessages, NotFoundError
from app.models.entity_version import EntityType, EntityVersion
from app.repositories.entity_version_repository import EntityVersionRepository
from app.schemas.common_schemas import Page


class EntityVersionService:
    def __init__(self, repository: EntityVersionRepository) -> None:
        self.repository = repository

    async def list_history(
        self, entity_type: EntityType, entity_id: UUID, skip: int = 0, limit: int = 10
    ) -> Page[EntityVersion]:
        items, total = await self.repository.list_by_entity(
            entity_type, entity_id, skip, limit
        )
        return Page(items=list(items), total=total, limit=limit, offset=skip)

    async def get_version(
        self, entity_type: EntityType, entity_id: UUID, version_number: int
    ) -> EntityVersion:
        version = await self.repository.get_version(
            entity_type, entity_id, version_number
        )
        if not version:
            raise NotFoundError(ErrorMessages.ENTITY_VERSION_NOT_FOUND)
        return version

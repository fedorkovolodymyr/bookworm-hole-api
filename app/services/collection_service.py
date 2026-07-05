from datetime import UTC, datetime
from uuid import UUID

from app.core.errors import BadRequestError, ErrorMessages, NotFoundError
from app.models.collection import Collection, CollectionItem
from app.repositories.collection_repository import CollectionRepository
from app.schemas.collection_schemas import (
    AddCollectionItemSchema,
    CollectionDetailResponse,
    CollectionItemResponse,
    CreateCollectionSchema,
    ReorderItemsSchema,
    UpdateCollectionItemSchema,
    UpdateCollectionSchema,
)
from app.schemas.common_schemas import Page


class CollectionService:
    def __init__(self, repository: CollectionRepository):
        self.repository = repository

    async def _get_visible(self, user_id: UUID, collection_id: UUID) -> Collection:
        collection = await self.repository.get_by_id(collection_id)
        if not collection or (
            not collection.is_public and collection.user_id != user_id
        ):
            raise NotFoundError(ErrorMessages.COLLECTION_NOT_FOUND)
        return collection

    async def _get_owned(self, user_id: UUID, collection_id: UUID) -> Collection:
        collection = await self.repository.get_by_id(collection_id)
        if not collection or collection.user_id != user_id:
            raise NotFoundError(ErrorMessages.COLLECTION_NOT_FOUND)
        return collection

    async def _get_owned_item(
        self, user_id: UUID, collection_id: UUID, item_id: UUID
    ) -> CollectionItem:
        await self._get_owned(user_id, collection_id)
        item = await self.repository.get_item_by_id(item_id)
        if not item or item.collection_id != collection_id:
            raise NotFoundError(ErrorMessages.COLLECTION_ITEM_NOT_FOUND)
        return item

    async def create_collection(
        self, user_id: UUID, new_collection: CreateCollectionSchema
    ) -> Collection:
        collection = Collection(user_id=user_id, **new_collection.model_dump())
        return await self.repository.create(collection)

    async def list_collections(
        self, user_id: UUID, skip: int = 0, limit: int = 10
    ) -> Page[Collection]:
        items, total = await self.repository.get_all_for_user(user_id, skip, limit)
        return Page(items=list(items), total=total, limit=limit, offset=skip)

    async def get_collection(
        self,
        user_id: UUID,
        collection_id: UUID,
        items_skip: int = 0,
        items_limit: int = 10,
    ) -> CollectionDetailResponse:
        collection = await self._get_visible(user_id, collection_id)
        items, total = await self.repository.get_items(
            collection_id, items_skip, items_limit
        )
        items_page = Page[CollectionItemResponse](
            items=[CollectionItemResponse.model_validate(item) for item in items],
            total=total,
            limit=items_limit,
            offset=items_skip,
        )
        return CollectionDetailResponse(
            id=collection.id,
            user_id=collection.user_id,
            name=collection.name,
            description=collection.description,
            is_public=collection.is_public,
            cover_image_url=collection.cover_image_url,
            sort_order=collection.sort_order,
            created_at=collection.created_at,
            updated_at=collection.updated_at,
            items=items_page,
        )

    async def update_collection(
        self, user_id: UUID, collection_id: UUID, data: UpdateCollectionSchema
    ) -> Collection:
        await self._get_owned(user_id, collection_id)
        collection = await self.repository.update(collection_id, data)
        if not collection:
            raise NotFoundError(ErrorMessages.COLLECTION_NOT_FOUND)
        return collection

    async def delete_collection(self, user_id: UUID, collection_id: UUID) -> None:
        await self._get_owned(user_id, collection_id)
        deleted = await self.repository.delete(collection_id)
        if not deleted:
            raise NotFoundError(ErrorMessages.COLLECTION_NOT_FOUND)

    async def add_item(
        self, user_id: UUID, collection_id: UUID, data: AddCollectionItemSchema
    ) -> CollectionItem:
        await self._get_owned(user_id, collection_id)
        position = await self.repository.get_next_position(collection_id)
        item = CollectionItem(
            collection_id=collection_id,
            position=position,
            added_at=datetime.now(UTC),
            **data.model_dump(),
        )
        return await self.repository.add_item(item)

    async def remove_item(
        self, user_id: UUID, collection_id: UUID, item_id: UUID
    ) -> None:
        await self._get_owned_item(user_id, collection_id, item_id)
        await self.repository.delete_item(item_id)

    async def update_item(
        self,
        user_id: UUID,
        collection_id: UUID,
        item_id: UUID,
        data: UpdateCollectionItemSchema,
    ) -> CollectionItem:
        await self._get_owned_item(user_id, collection_id, item_id)
        item = await self.repository.update_item(item_id, data)
        if not item:
            raise NotFoundError(ErrorMessages.COLLECTION_ITEM_NOT_FOUND)
        return item

    async def reorder_items(
        self, user_id: UUID, collection_id: UUID, reorder: ReorderItemsSchema
    ) -> None:
        await self._get_owned(user_id, collection_id)
        existing_ids = set(await self.repository.get_all_item_ids(collection_id))
        requested_ids = reorder.item_ids
        if (
            len(requested_ids) != len(set(requested_ids))
            or set(requested_ids) != existing_ids
        ):
            raise BadRequestError(ErrorMessages.REORDER_INVALID_ITEM_IDS)
        await self.repository.reorder_items(requested_ids)

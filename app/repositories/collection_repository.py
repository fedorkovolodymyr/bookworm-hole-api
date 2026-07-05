from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col, select

from app.models.collection import Collection, CollectionItem
from app.schemas.collection_schemas import (
    UpdateCollectionItemSchema,
    UpdateCollectionSchema,
)


class CollectionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, collection: Collection) -> Collection:
        self.session.add(collection)
        await self.session.commit()
        await self.session.refresh(collection)
        return collection

    async def get_by_id(self, collection_id: UUID) -> Collection | None:
        return await self.session.get(Collection, collection_id, populate_existing=True)

    async def get_all_for_user(
        self, user_id: UUID, skip: int = 0, limit: int = 10
    ) -> tuple[Sequence[Collection], int]:
        query = select(Collection).where(col(Collection.user_id) == user_id)
        count_query = select(func.count()).select_from(
            select(Collection.id).where(col(Collection.user_id) == user_id).subquery()
        )
        total = (await self.session.execute(count_query)).scalar_one()
        result = await self.session.execute(query.offset(skip).limit(limit))
        return result.scalars().all(), total

    async def update(
        self, collection_id: UUID, data: UpdateCollectionSchema
    ) -> Collection | None:
        collection = await self.session.get(Collection, collection_id)
        if not collection:
            return None
        collection.sqlmodel_update(data.model_dump(exclude_unset=True))
        self.session.add(collection)
        await self.session.commit()
        await self.session.refresh(collection)
        return collection

    async def delete(self, collection_id: UUID) -> bool:
        collection = await self.session.get(Collection, collection_id)
        if not collection:
            return False
        await self.session.delete(collection)
        await self.session.commit()
        return True

    async def get_items(
        self, collection_id: UUID, skip: int = 0, limit: int = 10
    ) -> tuple[Sequence[CollectionItem], int]:
        query = (
            select(CollectionItem)
            .where(col(CollectionItem.collection_id) == collection_id)
            .order_by(col(CollectionItem.position))
        )
        count_query = select(func.count()).select_from(
            select(CollectionItem.id)
            .where(col(CollectionItem.collection_id) == collection_id)
            .subquery()
        )
        total = (await self.session.execute(count_query)).scalar_one()
        result = await self.session.execute(query.offset(skip).limit(limit))
        return result.scalars().all(), total

    async def get_all_item_ids(self, collection_id: UUID) -> Sequence[UUID]:
        result = await self.session.execute(
            select(CollectionItem.id).where(
                col(CollectionItem.collection_id) == collection_id
            )
        )
        return result.scalars().all()

    async def get_next_position(self, collection_id: UUID) -> int:
        result = await self.session.execute(
            select(func.max(CollectionItem.position)).where(
                col(CollectionItem.collection_id) == collection_id
            )
        )
        max_position = result.scalar_one_or_none()
        return 0 if max_position is None else max_position + 1

    async def add_item(self, item: CollectionItem) -> CollectionItem:
        self.session.add(item)
        await self.session.commit()
        await self.session.refresh(item)
        return item

    async def get_item_by_id(self, item_id: UUID) -> CollectionItem | None:
        return await self.session.get(CollectionItem, item_id)

    async def update_item(
        self, item_id: UUID, data: UpdateCollectionItemSchema
    ) -> CollectionItem | None:
        item = await self.session.get(CollectionItem, item_id)
        if not item:
            return None
        item.sqlmodel_update(data.model_dump(exclude_unset=True))
        self.session.add(item)
        await self.session.commit()
        await self.session.refresh(item)
        return item

    async def delete_item(self, item_id: UUID) -> bool:
        item = await self.session.get(CollectionItem, item_id)
        if not item:
            return False
        await self.session.delete(item)
        await self.session.commit()
        return True

    async def reorder_items(self, ordered_item_ids: list[UUID]) -> None:
        result = await self.session.execute(
            select(CollectionItem).where(col(CollectionItem.id).in_(ordered_item_ids))
        )
        items_by_id = {item.id: item for item in result.scalars().all()}
        for position, item_id in enumerate(ordered_item_ids):
            items_by_id[item_id].position = position
        await self.session.commit()

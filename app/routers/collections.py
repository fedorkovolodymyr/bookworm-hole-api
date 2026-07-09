from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.deps import get_current_user
from app.models.user import User
from app.repositories.collection_repository import CollectionRepository
from app.schemas.collection_schemas import (
    AddCollectionItemSchema,
    CollectionDetailResponse,
    CollectionItemResponse,
    CollectionResponse,
    CreateCollectionSchema,
    ReorderItemsSchema,
    UpdateCollectionItemSchema,
    UpdateCollectionSchema,
)
from app.schemas.common_schemas import Page
from app.services.collection_service import CollectionService

collections_router = APIRouter(prefix="/collections", tags=["collections"])


def get_collection_service(
    session: AsyncSession = Depends(get_session),
) -> CollectionService:
    return CollectionService(CollectionRepository(session))


@collections_router.post(
    "/", response_model=CollectionResponse, status_code=status.HTTP_201_CREATED
)
async def create_collection(
    new_collection: CreateCollectionSchema,
    current_user: User = Depends(get_current_user),
    service: CollectionService = Depends(get_collection_service),
):
    return await service.create_collection(current_user.id, new_collection)


@collections_router.get("/", response_model=Page[CollectionResponse])
async def list_collections(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    service: CollectionService = Depends(get_collection_service),
):
    return await service.list_collections(current_user.id, skip, limit)


@collections_router.get("/{collection_id}", response_model=CollectionDetailResponse)
async def retrieve_collection(
    collection_id: UUID,
    items_skip: int = Query(0, ge=0),
    items_limit: int = Query(10, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    service: CollectionService = Depends(get_collection_service),
):
    return await service.get_collection(
        current_user.id, collection_id, items_skip, items_limit
    )


@collections_router.patch("/{collection_id}", response_model=CollectionResponse)
async def update_collection(
    collection_id: UUID,
    data: UpdateCollectionSchema,
    current_user: User = Depends(get_current_user),
    service: CollectionService = Depends(get_collection_service),
):
    return await service.update_collection(current_user.id, collection_id, data)


@collections_router.delete("/{collection_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_collection(
    collection_id: UUID,
    current_user: User = Depends(get_current_user),
    service: CollectionService = Depends(get_collection_service),
) -> None:
    await service.delete_collection(current_user.id, collection_id)


@collections_router.post(
    "/{collection_id}/items",
    response_model=CollectionItemResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_collection_item(
    collection_id: UUID,
    data: AddCollectionItemSchema,
    current_user: User = Depends(get_current_user),
    service: CollectionService = Depends(get_collection_service),
):
    return await service.add_item(current_user.id, collection_id, data)


@collections_router.delete(
    "/{collection_id}/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def remove_collection_item(
    collection_id: UUID,
    item_id: UUID,
    current_user: User = Depends(get_current_user),
    service: CollectionService = Depends(get_collection_service),
) -> None:
    await service.remove_item(current_user.id, collection_id, item_id)


@collections_router.patch(
    "/{collection_id}/items/{item_id}", response_model=CollectionItemResponse
)
async def update_collection_item(
    collection_id: UUID,
    item_id: UUID,
    data: UpdateCollectionItemSchema,
    current_user: User = Depends(get_current_user),
    service: CollectionService = Depends(get_collection_service),
):
    return await service.update_item(current_user.id, collection_id, item_id, data)


@collections_router.post(
    "/{collection_id}/reorder", status_code=status.HTTP_204_NO_CONTENT
)
async def reorder_collection_items(
    collection_id: UUID,
    data: ReorderItemsSchema,
    current_user: User = Depends(get_current_user),
    service: CollectionService = Depends(get_collection_service),
) -> None:
    await service.reorder_items(current_user.id, collection_id, data)

from collections.abc import AsyncIterator
from datetime import UTC, datetime

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.main import app
from app.models.catalog import Book as BookModel
from app.models.collection import Collection, CollectionItem
from app.models.user import User


def _login_as(user: User) -> None:
    app.dependency_overrides[get_current_user] = lambda: user


@pytest.fixture
async def owner(
    db_session: AsyncSession, async_client: AsyncClient
) -> AsyncIterator[User]:
    owner = User(email="owner@example.com", username="owner", display_name="Owner")
    db_session.add(owner)
    await db_session.commit()
    await db_session.refresh(owner)
    _login_as(owner)
    yield owner
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
async def other(db_session: AsyncSession) -> User:
    other = User(email="other@example.com", username="other", display_name="Other")
    db_session.add(other)
    await db_session.commit()
    await db_session.refresh(other)
    return other


@pytest.fixture
async def book(db_session: AsyncSession) -> BookModel:
    book = BookModel(title="Dune", description="Desert planet epic")
    db_session.add(book)
    await db_session.commit()
    await db_session.refresh(book)
    return book


@pytest.fixture
async def collection(db_session: AsyncSession, owner: User) -> Collection:
    collection = Collection(user_id=owner.id, name="Favourites")
    db_session.add(collection)
    await db_session.commit()
    await db_session.refresh(collection)
    return collection


@pytest.fixture
async def item(
    db_session: AsyncSession, collection: Collection, book: BookModel
) -> CollectionItem:
    item = CollectionItem(
        collection_id=collection.id,
        book_id=book.id,
        position=0,
        added_at=datetime.now(UTC),
    )
    db_session.add(item)
    await db_session.commit()
    await db_session.refresh(item)
    return item


class TestCreateCollection:
    async def test_requires_auth(self, async_client: AsyncClient):
        response = await async_client.post("/api/v1/collections/", json={"name": "X"})
        assert response.status_code == 401

    async def test_creates_collection(self, async_client: AsyncClient, owner: User):
        response = await async_client.post(
            "/api/v1/collections/",
            json={"name": "Favourites", "is_public": True},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["user_id"] == str(owner.id)
        assert data["name"] == "Favourites"
        assert data["is_public"] is True
        assert data["description"] is None
        assert data["sort_order"] == 0

    async def test_missing_name_returns_422(
        self, async_client: AsyncClient, owner: User
    ):
        response = await async_client.post("/api/v1/collections/", json={})
        assert response.status_code == 422


class TestListCollections:
    async def test_requires_auth(self, async_client: AsyncClient):
        response = await async_client.get("/api/v1/collections/")
        assert response.status_code == 401

    async def test_lists_only_own_collections(
        self,
        async_client: AsyncClient,
        owner: User,
        other: User,
        collection: Collection,
    ):
        response = await async_client.get("/api/v1/collections/")
        assert response.status_code == 200
        data = response.json()
        assert {item["id"] for item in data["items"]} == {str(collection.id)}

        _login_as(other)
        other_response = await async_client.get("/api/v1/collections/")
        assert other_response.json()["items"] == []

    async def test_rejects_limit_above_cap(
        self, async_client: AsyncClient, owner: User
    ):
        response = await async_client.get("/api/v1/collections/", params={"limit": 101})
        assert response.status_code == 422


class TestRetrieveCollection:
    async def test_owner_can_view_private(
        self,
        async_client: AsyncClient,
        owner: User,
        collection: Collection,
        item: CollectionItem,
    ):
        response = await async_client.get(f"/api/v1/collections/{collection.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(collection.id)
        assert data["items"]["total"] == 1
        assert data["items"]["items"][0]["id"] == str(item.id)

    async def test_non_owner_cannot_view_private(
        self,
        async_client: AsyncClient,
        owner: User,
        other: User,
        collection: Collection,
    ):
        _login_as(other)
        response = await async_client.get(f"/api/v1/collections/{collection.id}")
        assert response.status_code == 404

    async def test_anyone_can_view_public(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        owner: User,
        other: User,
        collection: Collection,
    ):
        collection.is_public = True
        db_session.add(collection)
        await db_session.commit()

        _login_as(other)
        response = await async_client.get(f"/api/v1/collections/{collection.id}")
        assert response.status_code == 200

    async def test_not_found(self, async_client: AsyncClient, owner: User):
        response = await async_client.get(
            "/api/v1/collections/00000000-0000-0000-0000-000000000000"
        )
        assert response.status_code == 404

    async def test_rejects_items_limit_above_cap(
        self, async_client: AsyncClient, owner: User, collection: Collection
    ):
        response = await async_client.get(
            f"/api/v1/collections/{collection.id}", params={"items_limit": 101}
        )
        assert response.status_code == 422


class TestUpdateCollection:
    @pytest.mark.parametrize(
        ("field", "value"),
        [
            ("name", "New Name"),
            ("description", "New description"),
            ("is_public", True),
            ("cover_image_url", "https://example.com/cover.jpg"),
        ],
    )
    async def test_updates_each_field(
        self,
        async_client: AsyncClient,
        owner: User,
        collection: Collection,
        field: str,
        value: object,
    ):
        response = await async_client.patch(
            f"/api/v1/collections/{collection.id}", json={field: value}
        )
        assert response.status_code == 200
        data = response.json()
        original = {
            "name": collection.name,
            "description": collection.description,
            "is_public": collection.is_public,
            "cover_image_url": collection.cover_image_url,
        }
        for name, original_value in original.items():
            assert data[name] == (value if name == field else original_value)

    async def test_not_found_for_non_owner(
        self,
        async_client: AsyncClient,
        owner: User,
        other: User,
        collection: Collection,
    ):
        _login_as(other)
        response = await async_client.patch(
            f"/api/v1/collections/{collection.id}", json={"name": "Hijacked"}
        )
        assert response.status_code == 404

    async def test_requires_auth(
        self, async_client: AsyncClient, owner: User, collection: Collection
    ):
        app.dependency_overrides.pop(get_current_user, None)
        response = await async_client.patch(
            f"/api/v1/collections/{collection.id}", json={"name": "Hijacked"}
        )
        assert response.status_code == 401


class TestDeleteCollection:
    async def test_deletes_and_cascades_items(
        self,
        async_client: AsyncClient,
        owner: User,
        collection: Collection,
        item: CollectionItem,
    ):
        response = await async_client.delete(f"/api/v1/collections/{collection.id}")
        assert response.status_code == 204

        follow_up = await async_client.get(f"/api/v1/collections/{collection.id}")
        assert follow_up.status_code == 404

    async def test_not_found_for_non_owner(
        self,
        async_client: AsyncClient,
        owner: User,
        other: User,
        collection: Collection,
    ):
        _login_as(other)
        response = await async_client.delete(f"/api/v1/collections/{collection.id}")
        assert response.status_code == 404

    async def test_not_found(self, async_client: AsyncClient, owner: User):
        response = await async_client.delete(
            "/api/v1/collections/00000000-0000-0000-0000-000000000000"
        )
        assert response.status_code == 404


class TestAddCollectionItem:
    async def test_adds_with_book_id(
        self,
        async_client: AsyncClient,
        owner: User,
        collection: Collection,
        book: BookModel,
    ):
        response = await async_client.post(
            f"/api/v1/collections/{collection.id}/items",
            json={"book_id": str(book.id), "note": "must read"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["collection_id"] == str(collection.id)
        assert data["book_id"] == str(book.id)
        assert data["release_id"] is None
        assert data["note"] == "must read"

    async def test_requires_exactly_one_target(
        self, async_client: AsyncClient, owner: User, collection: Collection
    ):
        response = await async_client.post(
            f"/api/v1/collections/{collection.id}/items", json={}
        )
        assert response.status_code == 422

    async def test_not_found_for_non_owner(
        self,
        async_client: AsyncClient,
        owner: User,
        other: User,
        collection: Collection,
        book: BookModel,
    ):
        _login_as(other)
        response = await async_client.post(
            f"/api/v1/collections/{collection.id}/items",
            json={"book_id": str(book.id)},
        )
        assert response.status_code == 404


class TestRemoveCollectionItem:
    async def test_removes_item(
        self,
        async_client: AsyncClient,
        owner: User,
        collection: Collection,
        item: CollectionItem,
    ):
        response = await async_client.delete(
            f"/api/v1/collections/{collection.id}/items/{item.id}"
        )
        assert response.status_code == 204

    async def test_not_found_for_wrong_item(
        self, async_client: AsyncClient, owner: User, collection: Collection
    ):
        response = await async_client.delete(
            f"/api/v1/collections/{collection.id}/items/"
            "00000000-0000-0000-0000-000000000000"
        )
        assert response.status_code == 404

    async def test_not_found_for_non_owner(
        self,
        async_client: AsyncClient,
        owner: User,
        other: User,
        collection: Collection,
        item: CollectionItem,
    ):
        _login_as(other)
        response = await async_client.delete(
            f"/api/v1/collections/{collection.id}/items/{item.id}"
        )
        assert response.status_code == 404


class TestUpdateCollectionItem:
    @pytest.mark.parametrize(
        ("field", "value"),
        [
            ("position", 5),
            ("note", "updated note"),
        ],
    )
    async def test_updates_each_field(
        self,
        async_client: AsyncClient,
        owner: User,
        collection: Collection,
        item: CollectionItem,
        field: str,
        value: object,
    ):
        response = await async_client.patch(
            f"/api/v1/collections/{collection.id}/items/{item.id}",
            json={field: value},
        )
        assert response.status_code == 200
        data = response.json()
        original = {"position": item.position, "note": item.note}
        for name, original_value in original.items():
            assert data[name] == (value if name == field else original_value)

    async def test_not_found_for_non_owner(
        self,
        async_client: AsyncClient,
        owner: User,
        other: User,
        collection: Collection,
        item: CollectionItem,
    ):
        _login_as(other)
        response = await async_client.patch(
            f"/api/v1/collections/{collection.id}/items/{item.id}",
            json={"note": "hijacked"},
        )
        assert response.status_code == 404


class TestReorderItems:
    @pytest.fixture
    async def second_item(
        self, db_session: AsyncSession, collection: Collection, book: BookModel
    ) -> CollectionItem:
        second = CollectionItem(
            collection_id=collection.id,
            book_id=book.id,
            position=1,
            added_at=datetime.now(UTC),
        )
        db_session.add(second)
        await db_session.commit()
        await db_session.refresh(second)
        return second

    async def test_reorders_atomically(
        self,
        async_client: AsyncClient,
        owner: User,
        collection: Collection,
        item: CollectionItem,
        second_item: CollectionItem,
    ):
        response = await async_client.post(
            f"/api/v1/collections/{collection.id}/reorder",
            json={"item_ids": [str(second_item.id), str(item.id)]},
        )
        assert response.status_code == 204

        detail = await async_client.get(f"/api/v1/collections/{collection.id}")
        ordered_ids = [i["id"] for i in detail.json()["items"]["items"]]
        assert ordered_ids == [str(second_item.id), str(item.id)]

    async def test_rejects_unknown_item_id(
        self,
        async_client: AsyncClient,
        owner: User,
        collection: Collection,
        item: CollectionItem,
    ):
        response = await async_client.post(
            f"/api/v1/collections/{collection.id}/reorder",
            json={"item_ids": ["00000000-0000-0000-0000-000000000000"]},
        )
        assert response.status_code == 400

    async def test_rejects_incomplete_list(
        self,
        async_client: AsyncClient,
        owner: User,
        collection: Collection,
        item: CollectionItem,
        second_item: CollectionItem,
    ):
        response = await async_client.post(
            f"/api/v1/collections/{collection.id}/reorder",
            json={"item_ids": [str(item.id)]},
        )
        assert response.status_code == 400

    async def test_rejects_duplicate_ids(
        self,
        async_client: AsyncClient,
        owner: User,
        collection: Collection,
        item: CollectionItem,
    ):
        response = await async_client.post(
            f"/api/v1/collections/{collection.id}/reorder",
            json={"item_ids": [str(item.id), str(item.id)]},
        )
        assert response.status_code == 400

    async def test_not_found_for_non_owner(
        self,
        async_client: AsyncClient,
        owner: User,
        other: User,
        collection: Collection,
        item: CollectionItem,
    ):
        _login_as(other)
        response = await async_client.post(
            f"/api/v1/collections/{collection.id}/reorder",
            json={"item_ids": [str(item.id)]},
        )
        assert response.status_code == 404

    async def test_requires_auth(
        self, async_client: AsyncClient, owner: User, collection: Collection
    ):
        app.dependency_overrides.pop(get_current_user, None)
        response = await async_client.post(
            f"/api/v1/collections/{collection.id}/reorder",
            json={"item_ids": []},
        )
        assert response.status_code == 401

from collections.abc import AsyncIterator
from datetime import UTC, datetime

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.main import app
from app.models.catalog import Book
from app.models.collection import Collection
from app.models.friendship import Friendship, FriendshipStatus
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
async def friend(db_session: AsyncSession) -> User:
    user = User(email="friend@example.com", username="friend", display_name="Friend")
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def stranger(db_session: AsyncSession) -> User:
    user = User(
        email="stranger@example.com", username="stranger", display_name="Stranger"
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def friendship(db_session: AsyncSession, owner: User, friend: User) -> None:
    db_session.add(
        Friendship(
            requester_id=owner.id,
            addressee_id=friend.id,
            status=FriendshipStatus.accepted,
            responded_at=datetime.now(UTC),
        )
    )
    await db_session.commit()


@pytest.fixture
async def book(db_session: AsyncSession) -> Book:
    book = Book(title="Dune", description="Desert planet epic")
    db_session.add(book)
    await db_session.commit()
    await db_session.refresh(book)
    return book


class TestShareBook:
    async def test_requires_auth(self, async_client: AsyncClient, book: Book):
        response = await async_client.post(
            f"/api/v1/share/book/{book.id}",
            json={"friend_id": "00000000-0000-0000-0000-000000000000", "message": "hi"},
        )
        assert response.status_code == 401

    async def test_returns_404_for_unknown_book(
        self, async_client: AsyncClient, owner: User, friend: User, friendship: None
    ):
        response = await async_client.post(
            "/api/v1/share/book/00000000-0000-0000-0000-000000000000",
            json={"friend_id": str(friend.id), "message": "check this out"},
        )
        assert response.status_code == 404

    async def test_returns_401_when_not_friends(
        self, async_client: AsyncClient, owner: User, stranger: User, book: Book
    ):
        response = await async_client.post(
            f"/api/v1/share/book/{book.id}",
            json={"friend_id": str(stranger.id), "message": "check this out"},
        )
        assert response.status_code == 401

    async def test_sends_chat_message_with_book_attachment(
        self,
        async_client: AsyncClient,
        owner: User,
        friend: User,
        friendship: None,
        book: Book,
    ):
        response = await async_client.post(
            f"/api/v1/share/book/{book.id}",
            json={"friend_id": str(friend.id), "message": "check this out"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["body"] == "check this out"
        assert data["attachment_book_id"] == str(book.id)
        assert data["sender_id"] == str(owner.id)


class TestShareCollection:
    async def test_requires_auth(self, async_client: AsyncClient):
        response = await async_client.post(
            "/api/v1/share/collection/00000000-0000-0000-0000-000000000000",
            json={"friend_id": "00000000-0000-0000-0000-000000000000", "message": "hi"},
        )
        assert response.status_code == 401

    async def test_returns_404_for_unknown_collection(
        self, async_client: AsyncClient, owner: User, friend: User, friendship: None
    ):
        response = await async_client.post(
            "/api/v1/share/collection/00000000-0000-0000-0000-000000000000",
            json={"friend_id": str(friend.id), "message": "check this out"},
        )
        assert response.status_code == 404

    async def test_shares_public_collection(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        owner: User,
        friend: User,
        friendship: None,
    ):
        collection = Collection(user_id=owner.id, name="Reads", is_public=True)
        db_session.add(collection)
        await db_session.commit()
        await db_session.refresh(collection)

        response = await async_client.post(
            f"/api/v1/share/collection/{collection.id}",
            json={"friend_id": str(friend.id), "message": "check this out"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["attachment_collection_id"] == str(collection.id)

    async def test_owner_can_share_private_collection(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        owner: User,
        friend: User,
        friendship: None,
    ):
        collection = Collection(user_id=owner.id, name="Private", is_public=False)
        db_session.add(collection)
        await db_session.commit()
        await db_session.refresh(collection)

        response = await async_client.post(
            f"/api/v1/share/collection/{collection.id}",
            json={"friend_id": str(friend.id), "message": "check this out"},
        )
        assert response.status_code == 200

    async def test_non_owner_cannot_share_private_collection(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        owner: User,
        friend: User,
        friendship: None,
    ):
        collection = Collection(user_id=friend.id, name="Private", is_public=False)
        db_session.add(collection)
        await db_session.commit()
        await db_session.refresh(collection)

        response = await async_client.post(
            f"/api/v1/share/collection/{collection.id}",
            json={"friend_id": str(friend.id), "message": "check this out"},
        )
        assert response.status_code == 401

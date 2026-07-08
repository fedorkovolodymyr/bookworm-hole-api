from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col

from app.core.deps import get_current_user
from app.main import app
from app.models.chat import ChatMessage
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
        )
    )
    await db_session.commit()


class TestStartChatThread:
    async def test_requires_auth(self, async_client: AsyncClient, friend: User):
        response = await async_client.post(
            "/api/v1/chat/threads", json={"recipient_id": str(friend.id)}
        )
        assert response.status_code == 401

    async def test_creates_thread_with_friend(
        self, async_client: AsyncClient, owner: User, friend: User, friendship: None
    ):
        response = await async_client.post(
            "/api/v1/chat/threads", json={"recipient_id": str(friend.id)}
        )
        assert response.status_code == 200
        data = response.json()
        assert {data["user_a_id"], data["user_b_id"]} == {
            str(owner.id),
            str(friend.id),
        }
        assert data["last_message_at"] is None

    async def test_returns_same_thread_on_repeat_call(
        self, async_client: AsyncClient, owner: User, friend: User, friendship: None
    ):
        first = await async_client.post(
            "/api/v1/chat/threads", json={"recipient_id": str(friend.id)}
        )
        second = await async_client.post(
            "/api/v1/chat/threads", json={"recipient_id": str(friend.id)}
        )
        assert first.json()["id"] == second.json()["id"]

    async def test_rejects_non_friend(
        self, async_client: AsyncClient, owner: User, stranger: User
    ):
        response = await async_client.post(
            "/api/v1/chat/threads", json={"recipient_id": str(stranger.id)}
        )
        assert response.status_code == 401

    async def test_rejects_self(self, async_client: AsyncClient, owner: User):
        response = await async_client.post(
            "/api/v1/chat/threads", json={"recipient_id": str(owner.id)}
        )
        assert response.status_code == 401


async def _create_thread(async_client: AsyncClient, friend: User) -> str:
    response = await async_client.post(
        "/api/v1/chat/threads", json={"recipient_id": str(friend.id)}
    )
    return response.json()["id"]


class TestListChatThreads:
    async def test_requires_auth(self, async_client: AsyncClient):
        response = await async_client.get("/api/v1/chat/threads/")
        assert response.status_code == 401

    async def test_returns_empty_list_when_no_threads(
        self, async_client: AsyncClient, owner: User
    ):
        response = await async_client.get("/api/v1/chat/threads/")
        assert response.status_code == 200
        assert response.json() == []

    async def test_lists_thread_with_last_message_preview(
        self, async_client: AsyncClient, owner: User, friend: User, friendship: None
    ):
        thread_id = await _create_thread(async_client, friend)
        send_response = await async_client.post(
            f"/api/v1/chat/threads/{thread_id}/messages",
            json={"body": "hello"},
        )
        assert send_response.status_code == 200

        response = await async_client.get("/api/v1/chat/threads/")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["id"] == thread_id
        assert data[0]["last_message"]["body"] == "hello"


class TestSendMessage:
    async def test_requires_auth(self, async_client: AsyncClient):
        response = await async_client.post(
            "/api/v1/chat/threads/00000000-0000-0000-0000-000000000000/messages",
            json={"body": "hi"},
        )
        assert response.status_code == 401

    async def test_returns_404_for_unknown_thread(
        self, async_client: AsyncClient, owner: User
    ):
        response = await async_client.post(
            "/api/v1/chat/threads/00000000-0000-0000-0000-000000000000/messages",
            json={"body": "hi"},
        )
        assert response.status_code == 404

    async def test_sends_message_and_updates_thread_last_message_at(
        self, async_client: AsyncClient, owner: User, friend: User, friendship: None
    ):
        thread_id = await _create_thread(async_client, friend)
        response = await async_client.post(
            f"/api/v1/chat/threads/{thread_id}/messages",
            json={"body": "hello there"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["thread_id"] == thread_id
        assert data["sender_id"] == str(owner.id)
        assert data["body"] == "hello there"
        assert data["read_at"] is None

    async def test_returns_404_when_not_a_thread_participant(
        self,
        async_client: AsyncClient,
        owner: User,
        friend: User,
        friendship: None,
        db_session: AsyncSession,
        stranger: User,
    ):
        thread_id = await _create_thread(async_client, friend)
        _login_as(stranger)
        try:
            response = await async_client.post(
                f"/api/v1/chat/threads/{thread_id}/messages",
                json={"body": "sneaky"},
            )
        finally:
            _login_as(owner)
        assert response.status_code == 404


class TestGetThreadMessages:
    async def test_requires_auth(self, async_client: AsyncClient):
        response = await async_client.get(
            "/api/v1/chat/threads/00000000-0000-0000-0000-000000000000/messages"
        )
        assert response.status_code == 401

    async def test_returns_404_for_unknown_thread(
        self, async_client: AsyncClient, owner: User
    ):
        response = await async_client.get(
            "/api/v1/chat/threads/00000000-0000-0000-0000-000000000000/messages"
        )
        assert response.status_code == 404

    async def test_returns_messages_newest_first(
        self,
        async_client: AsyncClient,
        owner: User,
        friend: User,
        friendship: None,
        db_session: AsyncSession,
    ):
        thread_id = await _create_thread(async_client, friend)
        base = datetime.now(UTC)
        first = ChatMessage(thread_id=thread_id, sender_id=owner.id, body="first")
        second = ChatMessage(thread_id=thread_id, sender_id=owner.id, body="second")
        db_session.add(first)
        db_session.add(second)
        await db_session.flush()
        await db_session.execute(
            update(ChatMessage)
            .where(col(ChatMessage.id) == first.id)
            .values(created_at=base)
        )
        await db_session.execute(
            update(ChatMessage)
            .where(col(ChatMessage.id) == second.id)
            .values(created_at=base + timedelta(seconds=1))
        )
        await db_session.commit()

        response = await async_client.get(f"/api/v1/chat/threads/{thread_id}/messages")
        assert response.status_code == 200
        data = response.json()
        assert [m["body"] for m in data] == ["second", "first"]

    async def test_respects_limit(
        self, async_client: AsyncClient, owner: User, friend: User, friendship: None
    ):
        thread_id = await _create_thread(async_client, friend)
        for body in ("a", "b", "c"):
            await async_client.post(
                f"/api/v1/chat/threads/{thread_id}/messages", json={"body": body}
            )

        response = await async_client.get(
            f"/api/v1/chat/threads/{thread_id}/messages", params={"limit": 2}
        )
        assert response.status_code == 200
        assert len(response.json()) == 2


class TestMarkThreadRead:
    async def test_requires_auth(self, async_client: AsyncClient):
        response = await async_client.post(
            "/api/v1/chat/threads/00000000-0000-0000-0000-000000000000/read"
        )
        assert response.status_code == 401

    async def test_returns_404_for_unknown_thread(
        self, async_client: AsyncClient, owner: User
    ):
        response = await async_client.post(
            "/api/v1/chat/threads/00000000-0000-0000-0000-000000000000/read"
        )
        assert response.status_code == 404

    async def test_marks_friend_messages_as_read(
        self, async_client: AsyncClient, owner: User, friend: User, friendship: None
    ):
        thread_id = await _create_thread(async_client, friend)
        _login_as(friend)
        try:
            await async_client.post(
                f"/api/v1/chat/threads/{thread_id}/messages",
                json={"body": "from friend"},
            )
        finally:
            _login_as(owner)

        response = await async_client.post(f"/api/v1/chat/threads/{thread_id}/read")
        assert response.status_code == 204

        messages = await async_client.get(f"/api/v1/chat/threads/{thread_id}/messages")
        assert messages.json()[0]["read_at"] is not None

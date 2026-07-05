from collections.abc import AsyncIterator
from datetime import UTC, datetime

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.main import app
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
async def other(db_session: AsyncSession) -> User:
    other = User(email="other@example.com", username="other", display_name="Other")
    db_session.add(other)
    await db_session.commit()
    await db_session.refresh(other)
    return other


@pytest.fixture
async def third(db_session: AsyncSession) -> User:
    third = User(email="third@example.com", username="third", display_name="Third")
    db_session.add(third)
    await db_session.commit()
    await db_session.refresh(third)
    return third


async def _make_friendship(
    db_session: AsyncSession,
    requester: User,
    addressee: User,
    status: FriendshipStatus,
    responded_at: datetime | None = None,
) -> Friendship:
    friendship = Friendship(
        requester_id=requester.id,
        addressee_id=addressee.id,
        status=status,
        responded_at=responded_at,
    )
    db_session.add(friendship)
    await db_session.commit()
    await db_session.refresh(friendship)
    return friendship


class TestSendFriendRequest:
    async def test_requires_auth(self, async_client: AsyncClient):
        response = await async_client.post(
            "/api/v1/friends/requests", json={"username": "other"}
        )
        assert response.status_code == 401

    async def test_creates_pending_request(
        self, async_client: AsyncClient, owner: User, other: User
    ):
        response = await async_client.post(
            "/api/v1/friends/requests", json={"username": "other"}
        )
        assert response.status_code == 201
        data = response.json()
        assert data["requester_id"] == str(owner.id)
        assert data["addressee_id"] == str(other.id)
        assert data["status"] == "pending"
        assert data["responded_at"] is None

    async def test_unknown_username_returns_404(
        self, async_client: AsyncClient, owner: User
    ):
        response = await async_client.post(
            "/api/v1/friends/requests", json={"username": "ghost"}
        )
        assert response.status_code == 404

    async def test_self_request_returns_400(
        self, async_client: AsyncClient, owner: User
    ):
        response = await async_client.post(
            "/api/v1/friends/requests", json={"username": "owner"}
        )
        assert response.status_code == 400

    async def test_duplicate_same_direction_returns_409(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        owner: User,
        other: User,
    ):
        await _make_friendship(db_session, owner, other, FriendshipStatus.pending)
        response = await async_client.post(
            "/api/v1/friends/requests", json={"username": "other"}
        )
        assert response.status_code == 409

    async def test_opposite_direction_pending_auto_accepts(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        owner: User,
        other: User,
    ):
        await _make_friendship(db_session, other, owner, FriendshipStatus.pending)
        response = await async_client.post(
            "/api/v1/friends/requests", json={"username": "other"}
        )
        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "accepted"
        assert data["requester_id"] == str(other.id)
        assert data["responded_at"] is not None

    async def test_already_friends_returns_409(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        owner: User,
        other: User,
    ):
        await _make_friendship(
            db_session,
            owner,
            other,
            FriendshipStatus.accepted,
            responded_at=datetime.now(UTC),
        )
        response = await async_client.post(
            "/api/v1/friends/requests", json={"username": "other"}
        )
        assert response.status_code == 409

    async def test_blocked_returns_409(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        owner: User,
        other: User,
    ):
        await _make_friendship(
            db_session,
            other,
            owner,
            FriendshipStatus.blocked,
            responded_at=datetime.now(UTC),
        )
        response = await async_client.post(
            "/api/v1/friends/requests", json={"username": "other"}
        )
        assert response.status_code == 409

    async def test_re_request_after_decline_resets_row(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        owner: User,
        other: User,
    ):
        declined = await _make_friendship(
            db_session,
            other,
            owner,
            FriendshipStatus.declined,
            responded_at=datetime.now(UTC),
        )
        response = await async_client.post(
            "/api/v1/friends/requests", json={"username": "other"}
        )
        assert response.status_code == 201
        data = response.json()
        assert data["id"] == str(declined.id)
        assert data["status"] == "pending"
        assert data["requester_id"] == str(owner.id)
        assert data["responded_at"] is None


class TestIncomingOutgoingRequests:
    async def test_lists_incoming_and_outgoing(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        owner: User,
        other: User,
        third: User,
    ):
        incoming = await _make_friendship(
            db_session, other, owner, FriendshipStatus.pending
        )
        outgoing = await _make_friendship(
            db_session, owner, third, FriendshipStatus.pending
        )

        incoming_response = await async_client.get("/api/v1/friends/requests/incoming")
        assert incoming_response.status_code == 200
        assert [r["id"] for r in incoming_response.json()] == [str(incoming.id)]

        outgoing_response = await async_client.get("/api/v1/friends/requests/outgoing")
        assert outgoing_response.status_code == 200
        assert [r["id"] for r in outgoing_response.json()] == [str(outgoing.id)]

    async def test_requires_auth(self, async_client: AsyncClient):
        incoming = await async_client.get("/api/v1/friends/requests/incoming")
        outgoing = await async_client.get("/api/v1/friends/requests/outgoing")
        assert incoming.status_code == 401
        assert outgoing.status_code == 401


class TestAcceptDeclineRequest:
    async def test_addressee_can_accept(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        owner: User,
        other: User,
    ):
        request = await _make_friendship(
            db_session, other, owner, FriendshipStatus.pending
        )
        response = await async_client.post(
            f"/api/v1/friends/requests/{request.id}/accept"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "accepted"
        assert data["responded_at"] is not None

    async def test_addressee_can_decline(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        owner: User,
        other: User,
    ):
        request = await _make_friendship(
            db_session, other, owner, FriendshipStatus.pending
        )
        response = await async_client.post(
            f"/api/v1/friends/requests/{request.id}/decline"
        )
        assert response.status_code == 200
        assert response.json()["status"] == "declined"

    async def test_requester_cannot_accept_own_request(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        owner: User,
        other: User,
    ):
        request = await _make_friendship(
            db_session, owner, other, FriendshipStatus.pending
        )
        response = await async_client.post(
            f"/api/v1/friends/requests/{request.id}/accept"
        )
        assert response.status_code == 404

    async def test_not_found(self, async_client: AsyncClient, owner: User):
        response = await async_client.post(
            "/api/v1/friends/requests/00000000-0000-0000-0000-000000000000/accept"
        )
        assert response.status_code == 404

    async def test_already_accepted_cannot_be_accepted_again(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        owner: User,
        other: User,
    ):
        request = await _make_friendship(
            db_session,
            other,
            owner,
            FriendshipStatus.accepted,
            responded_at=datetime.now(UTC),
        )
        response = await async_client.post(
            f"/api/v1/friends/requests/{request.id}/accept"
        )
        assert response.status_code == 404


class TestListFriends:
    async def test_lists_only_accepted_both_directions(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        owner: User,
        other: User,
        third: User,
    ):
        await _make_friendship(
            db_session,
            owner,
            other,
            FriendshipStatus.accepted,
            responded_at=datetime.now(UTC),
        )
        await _make_friendship(
            db_session,
            third,
            owner,
            FriendshipStatus.accepted,
            responded_at=datetime.now(UTC),
        )

        response = await async_client.get("/api/v1/friends/")
        assert response.status_code == 200
        user_ids = {f["user_id"] for f in response.json()}
        assert user_ids == {str(other.id), str(third.id)}

    async def test_excludes_pending_and_blocked(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        owner: User,
        other: User,
        third: User,
    ):
        await _make_friendship(db_session, owner, other, FriendshipStatus.pending)
        await _make_friendship(
            db_session,
            owner,
            third,
            FriendshipStatus.blocked,
            responded_at=datetime.now(UTC),
        )
        response = await async_client.get("/api/v1/friends/")
        assert response.status_code == 200
        assert response.json() == []

    async def test_requires_auth(self, async_client: AsyncClient):
        response = await async_client.get("/api/v1/friends/")
        assert response.status_code == 401


class TestUnfriend:
    async def test_unfriends(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        owner: User,
        other: User,
    ):
        await _make_friendship(
            db_session,
            other,
            owner,
            FriendshipStatus.accepted,
            responded_at=datetime.now(UTC),
        )
        response = await async_client.delete(f"/api/v1/friends/{other.id}")
        assert response.status_code == 204

        friends = await async_client.get("/api/v1/friends/")
        assert friends.json() == []

    async def test_not_found_when_not_friends(
        self, async_client: AsyncClient, owner: User, other: User
    ):
        response = await async_client.delete(f"/api/v1/friends/{other.id}")
        assert response.status_code == 404

    async def test_requires_auth(self, async_client: AsyncClient, other: User):
        response = await async_client.delete(f"/api/v1/friends/{other.id}")
        assert response.status_code == 401


class TestBlockUser:
    async def test_blocks_new_pair(
        self, async_client: AsyncClient, owner: User, other: User
    ):
        response = await async_client.post(f"/api/v1/friends/{other.id}/block")
        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "blocked"
        assert data["requester_id"] == str(owner.id)
        assert data["addressee_id"] == str(other.id)

    async def test_blocks_existing_friendship(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        owner: User,
        other: User,
    ):
        await _make_friendship(
            db_session,
            other,
            owner,
            FriendshipStatus.accepted,
            responded_at=datetime.now(UTC),
        )
        response = await async_client.post(f"/api/v1/friends/{other.id}/block")
        assert response.status_code == 201
        assert response.json()["status"] == "blocked"

        friends = await async_client.get("/api/v1/friends/")
        assert friends.json() == []

    async def test_cannot_block_self(self, async_client: AsyncClient, owner: User):
        response = await async_client.post(f"/api/v1/friends/{owner.id}/block")
        assert response.status_code == 400

    async def test_unknown_user_returns_404(
        self, async_client: AsyncClient, owner: User
    ):
        response = await async_client.post(
            "/api/v1/friends/00000000-0000-0000-0000-000000000000/block"
        )
        assert response.status_code == 404

    async def test_blocked_user_cannot_send_new_request(
        self,
        async_client: AsyncClient,
        owner: User,
        other: User,
    ):
        await async_client.post(f"/api/v1/friends/{other.id}/block")
        _login_as(other)
        response = await async_client.post(
            "/api/v1/friends/requests", json={"username": "owner"}
        )
        assert response.status_code == 409

    async def test_requires_auth(self, async_client: AsyncClient, other: User):
        response = await async_client.post(f"/api/v1/friends/{other.id}/block")
        assert response.status_code == 401


class TestUnblockUser:
    async def test_blocker_can_unblock(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        owner: User,
        other: User,
    ):
        await _make_friendship(
            db_session,
            owner,
            other,
            FriendshipStatus.blocked,
            responded_at=datetime.now(UTC),
        )
        response = await async_client.delete(f"/api/v1/friends/{other.id}/block")
        assert response.status_code == 204

        follow_up = await async_client.post(
            "/api/v1/friends/requests", json={"username": "other"}
        )
        assert follow_up.status_code == 201

    async def test_non_blocker_cannot_unblock(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        owner: User,
        other: User,
    ):
        await _make_friendship(
            db_session,
            other,
            owner,
            FriendshipStatus.blocked,
            responded_at=datetime.now(UTC),
        )
        response = await async_client.delete(f"/api/v1/friends/{other.id}/block")
        assert response.status_code == 404

    async def test_not_found_when_no_block(
        self, async_client: AsyncClient, owner: User, other: User
    ):
        response = await async_client.delete(f"/api/v1/friends/{other.id}/block")
        assert response.status_code == 404

    async def test_requires_auth(self, async_client: AsyncClient, other: User):
        response = await async_client.delete(f"/api/v1/friends/{other.id}/block")
        assert response.status_code == 401

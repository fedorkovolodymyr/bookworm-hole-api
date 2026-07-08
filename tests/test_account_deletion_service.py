from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.models.catalog import Book, Release, ReleaseFormat
from app.models.collection import Collection
from app.models.friendship import Friendship, FriendshipStatus
from app.models.reading_session import ReadingSession
from app.models.review import Review
from app.models.user import User
from app.repositories.account_deletion_repository import AccountDeletionRepository
from app.repositories.user_repository import UserRepository
from app.services.account_deletion_service import AccountDeletionService


async def _make_user(
    db_session: AsyncSession, *, email: str, deletion_scheduled_at: datetime | None
) -> User:
    user = User(
        email=email,
        username=email.split("@")[0],
        display_name=email,
        deletion_scheduled_at=deletion_scheduled_at,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
def service(db_session: AsyncSession) -> AccountDeletionService:
    return AccountDeletionService(
        UserRepository(db_session), AccountDeletionRepository(db_session)
    )


class TestPurgeDeletedUsers:
    async def test_hard_deletes_user_past_grace_period(
        self, db_session: AsyncSession, service: AccountDeletionService
    ):
        user = await _make_user(
            db_session,
            email="expired@example.com",
            deletion_scheduled_at=datetime.now(UTC) - timedelta(days=1),
        )

        summary = await service.purge_deleted_users()

        assert summary.purged == 1
        assert await db_session.get(User, user.id) is None

    async def test_leaves_user_within_grace_period_untouched(
        self, db_session: AsyncSession, service: AccountDeletionService
    ):
        user = await _make_user(
            db_session,
            email="active@example.com",
            deletion_scheduled_at=datetime.now(UTC) + timedelta(days=1),
        )

        summary = await service.purge_deleted_users()

        assert summary.purged == 0
        assert await db_session.get(User, user.id) is not None

    async def test_leaves_user_with_no_deletion_scheduled_untouched(
        self, db_session: AsyncSession, service: AccountDeletionService
    ):
        user = await _make_user(
            db_session, email="never@example.com", deletion_scheduled_at=None
        )

        summary = await service.purge_deleted_users()

        assert summary.purged == 0
        assert await db_session.get(User, user.id) is not None

    async def test_anonymizes_review_authorship_instead_of_deleting_it(
        self, db_session: AsyncSession, service: AccountDeletionService
    ):
        user = await _make_user(
            db_session,
            email="reviewer@example.com",
            deletion_scheduled_at=datetime.now(UTC) - timedelta(days=1),
        )
        book = Book(title="Dune", description="Desert planet epic")
        db_session.add(book)
        await db_session.flush()
        review = Review(user_id=user.id, book_id=book.id, rating=5, body="Great book")
        db_session.add(review)
        await db_session.commit()
        await db_session.refresh(review)

        await service.purge_deleted_users()

        reloaded = await db_session.get(Review, review.id)
        assert reloaded is not None
        assert reloaded.user_id is None
        assert reloaded.body == "Great book"

    async def test_hard_deletes_dependent_personal_data(
        self, db_session: AsyncSession, service: AccountDeletionService
    ):
        user = await _make_user(
            db_session,
            email="fulldata@example.com",
            deletion_scheduled_at=datetime.now(UTC) - timedelta(days=1),
        )
        other = await _make_user(
            db_session, email="friend@example.com", deletion_scheduled_at=None
        )
        db_session.add(Collection(user_id=user.id, name="My Books"))
        db_session.add(
            Friendship(
                requester_id=user.id,
                addressee_id=other.id,
                status=FriendshipStatus.accepted,
            )
        )
        release_book = Book(title="Foundation", description="Empire falls")
        db_session.add(release_book)
        await db_session.flush()
        await db_session.commit()

        await service.purge_deleted_users()

        collections = (
            (
                await db_session.execute(
                    select(Collection).where(Collection.user_id == user.id)
                )
            )
            .scalars()
            .all()
        )
        friendships = (await db_session.execute(select(Friendship))).scalars().all()
        assert collections == []
        assert friendships == []
        assert await db_session.get(User, other.id) is not None

    async def test_purges_multiple_users(
        self, db_session: AsyncSession, service: AccountDeletionService
    ):
        expired_at = datetime.now(UTC) - timedelta(days=1)
        first = await _make_user(
            db_session, email="one@example.com", deletion_scheduled_at=expired_at
        )
        second = await _make_user(
            db_session, email="two@example.com", deletion_scheduled_at=expired_at
        )

        summary = await service.purge_deleted_users()

        assert summary.purged == 2
        assert await db_session.get(User, first.id) is None
        assert await db_session.get(User, second.id) is None


class TestAccountDeletionRepositoryReadingSessionCleanup:
    async def test_deletes_reading_sessions_for_purged_user(
        self, db_session: AsyncSession, service: AccountDeletionService
    ):
        user = await _make_user(
            db_session,
            email="reader@example.com",
            deletion_scheduled_at=datetime.now(UTC) - timedelta(days=1),
        )
        book = Book(title="Dune", description="Desert planet epic")
        db_session.add(book)
        await db_session.flush()
        release = Release(
            book_id=book.id,
            format=ReleaseFormat.hardcover,
            publisher="Test Publisher",
            language="en",
        )
        db_session.add(release)
        await db_session.flush()
        db_session.add(
            ReadingSession(
                user_id=user.id,
                release_id=release.id,
                started_at=datetime.now(UTC),
            )
        )
        await db_session.commit()

        await service.purge_deleted_users()

        remaining = (
            (
                await db_session.execute(
                    select(ReadingSession).where(ReadingSession.user_id == user.id)
                )
            )
            .scalars()
            .all()
        )
        assert remaining == []

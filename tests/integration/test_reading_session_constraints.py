from datetime import UTC, datetime

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.catalog import Book, Release, ReleaseFormat
from app.models.reading_session import ReadingSession
from app.models.user import User


@pytest.fixture
async def user_and_release(db_session: AsyncSession) -> tuple[User, Release]:
    user = User(email="reader@example.com", username="reader", display_name="Reader")
    db_session.add(user)

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
    await db_session.commit()

    return user, release


class TestActiveSessionUniqueness:
    async def test_two_ended_sessions_can_coexist(
        self, db_session: AsyncSession, user_and_release: tuple[User, Release]
    ):
        user, release = user_and_release
        now = datetime.now(UTC)

        db_session.add_all(
            [
                ReadingSession(
                    user_id=user.id,
                    release_id=release.id,
                    started_at=now,
                    ended_at=now,
                ),
                ReadingSession(
                    user_id=user.id,
                    release_id=release.id,
                    started_at=now,
                    ended_at=now,
                ),
            ]
        )

        await db_session.commit()

    async def test_second_open_session_raises_integrity_error(
        self, db_session: AsyncSession, user_and_release: tuple[User, Release]
    ):
        user, release = user_and_release
        now = datetime.now(UTC)

        db_session.add(
            ReadingSession(user_id=user.id, release_id=release.id, started_at=now)
        )
        await db_session.commit()

        db_session.add(
            ReadingSession(user_id=user.id, release_id=release.id, started_at=now)
        )
        with pytest.raises(IntegrityError):
            await db_session.commit()

    async def test_open_session_allowed_after_previous_one_ends(
        self, db_session: AsyncSession, user_and_release: tuple[User, Release]
    ):
        user, release = user_and_release
        now = datetime.now(UTC)

        first = ReadingSession(user_id=user.id, release_id=release.id, started_at=now)
        db_session.add(first)
        await db_session.commit()

        first.ended_at = now
        await db_session.commit()

        db_session.add(
            ReadingSession(user_id=user.id, release_id=release.id, started_at=now)
        )
        await db_session.commit()

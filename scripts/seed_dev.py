import asyncio
from datetime import UTC, datetime, timedelta
from random import Random

from faker import Faker
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.db import async_session_factory
from app.models.book_status import BookStatus, BookStatusKind
from app.models.catalog import Book, Release
from app.models.collection import Collection, CollectionItem
from app.models.friendship import Friendship, FriendshipStatus
from app.models.reading_session import PositionUnit, ReadingSession
from app.models.review import Review
from app.models.user import User
from app.services.security import hash_password

DEV_USER_CREDENTIALS = [
    ("alice", "alice@bookwormhole.test", "Alice Anderson"),
    ("bob", "bob@bookwormhole.test", "Bob Baker"),
    ("carol", "carol@bookwormhole.test", "Carol Chen"),
    ("dave", "dave@bookwormhole.test", "Dave Davis"),
    ("eve", "eve@bookwormhole.test", "Eve Evans"),
]

COMMON_PASSWORD = "dev1234"
RANDOM_SEED = 42


async def create_dev_users(session: AsyncSession) -> dict[str, User]:
    """Create or retrieve 5 dev users."""
    users: dict[str, User] = {}
    for username, email, display_name in DEV_USER_CREDENTIALS:
        existing = await session.execute(select(User).where(User.email == email))
        user = existing.scalars().first()
        if user is None:
            user = User(
                email=email,
                username=username,
                display_name=display_name,
                password_hash=hash_password(COMMON_PASSWORD),
                bio=f"{display_name} is a book lover.",
                is_active=True,
            )
            session.add(user)
        users[username] = user
    await session.flush()
    return users


async def create_friendships(session: AsyncSession, users: dict[str, User]) -> None:
    """Create friendship graph: alice ↔ bob, alice ↔ carol, bob ↔ dave."""
    friendship_pairs = [
        ("alice", "bob"),
        ("alice", "carol"),
        ("bob", "dave"),
    ]

    for user1_key, user2_key in friendship_pairs:
        user1 = users[user1_key]
        user2 = users[user2_key]

        # Check forward direction
        existing = await session.execute(
            select(Friendship).where(
                (Friendship.requester_id == user1.id)
                & (Friendship.addressee_id == user2.id)
            )
        )
        if not existing.scalars().first():
            friendship = Friendship(
                requester_id=user1.id,
                addressee_id=user2.id,
                status=FriendshipStatus.accepted,
                responded_at=datetime.now(UTC),
            )
            session.add(friendship)

        # Check reverse direction
        existing = await session.execute(
            select(Friendship).where(
                (Friendship.requester_id == user2.id)
                & (Friendship.addressee_id == user1.id)
            )
        )
        if not existing.scalars().first():
            friendship = Friendship(
                requester_id=user2.id,
                addressee_id=user1.id,
                status=FriendshipStatus.accepted,
                responded_at=datetime.now(UTC),
            )
            session.add(friendship)

    await session.flush()


async def seed_dev_data() -> None:
    """Seed dev data: users, book statuses, collections, reviews, reading sessions."""
    async with async_session_factory() as session:
        # Create users
        users = await create_dev_users(session)
        logger.info(f"Created {len(users)} dev users")

        # Get all books and releases
        books_result = await session.execute(select(Book))
        books = books_result.scalars().all()
        if not books:
            logger.warning("No books found. Run task seed:catalog first.")
            return

        releases_result = await session.execute(select(Release))
        releases = releases_result.scalars().all()
        logger.info(f"Found {len(books)} books and {len(releases)} releases")

        # Use seeded random for deterministic output
        rng = Random(RANDOM_SEED)
        faker = Faker()
        faker.seed_instance(RANDOM_SEED)

        # Distribute books across users and statuses
        statuses = [
            BookStatusKind.owned,
            BookStatusKind.wishlist,
            BookStatusKind.pre_order,
            BookStatusKind.lent_out,
            BookStatusKind.borrowed,
            BookStatusKind.gifted_away,
            BookStatusKind.sold,
        ]

        book_status_count = 0
        review_count = 0
        collection_count = 0
        reading_session_count = 0

        for username, user in users.items():
            # Create 20+ book statuses per user
            sampled_books = rng.sample(books, min(25, len(books)))
            sampled_releases = rng.sample(releases, min(25, len(releases)))

            for idx, book in enumerate(sampled_books):
                status = statuses[idx % len(statuses)]
                acquired_at = datetime.now(UTC) - timedelta(days=rng.randint(1, 730))
                book_status = BookStatus(
                    user_id=user.id,
                    book_id=book.id,
                    status=status,
                    acquired_at=acquired_at,
                    notes=(
                        faker.sentence() if status == BookStatusKind.lent_out else None
                    ),
                )
                session.add(book_status)
                book_status_count += 1

            for idx, release in enumerate(sampled_releases):
                status = statuses[(idx + 2) % len(statuses)]
                acquired_at = datetime.now(UTC) - timedelta(days=rng.randint(1, 730))
                book_status = BookStatus(
                    user_id=user.id,
                    release_id=release.id,
                    status=status,
                    acquired_at=acquired_at,
                )
                session.add(book_status)
                book_status_count += 1

            # Create collections for each user
            for coll_idx in range(2):
                collection = Collection(
                    user_id=user.id,
                    name=f"{username.title()}'s Collection {coll_idx + 1}",
                    description=faker.sentence(),
                    is_public=rng.choice([True, False]),
                )
                session.add(collection)
                await session.flush()
                collection_count += 1

                # Add books to collection
                selected_books = rng.sample(sampled_books, min(5, len(sampled_books)))
                for item_idx, book in enumerate(selected_books):
                    item = CollectionItem(
                        collection_id=collection.id,
                        book_id=book.id,
                        position=item_idx,
                        added_at=datetime.now(UTC),
                        note=faker.sentence() if rng.choice([True, False]) else None,
                    )
                    session.add(item)

            # Create reviews (6 per user)
            for _ in range(6):
                target_book = rng.choice(sampled_books)
                review = Review(
                    user_id=user.id,
                    book_id=target_book.id,
                    rating=rng.randint(1, 5),
                    title=faker.sentence(),
                    body=faker.paragraph(),
                    is_public=rng.choice([True, False]),
                    contains_spoilers=rng.choice([True, False]),
                )
                session.add(review)
                review_count += 1

            # Create reading sessions (10+ per user)
            for release in sampled_releases[:10]:
                started_at = datetime.now(UTC) - timedelta(days=rng.randint(1, 180))
                ended_at = (
                    started_at + timedelta(days=rng.randint(5, 60))
                    if rng.choice([True, False])
                    else None
                )

                session_obj = ReadingSession(
                    user_id=user.id,
                    release_id=release.id,
                    started_at=started_at,
                    ended_at=ended_at,
                    pages_read=rng.randint(10, 300) if ended_at else None,
                    position_start=0,
                    position_end=rng.randint(10, 300) if ended_at else None,
                    position_unit=PositionUnit.page,
                    notes=faker.sentence() if rng.choice([True, False]) else None,
                )
                session.add(session_obj)
                reading_session_count += 1

        await session.flush()

        # Create friendships
        await create_friendships(session, users)

        # Commit all changes
        await session.commit()

        logger.info(
            f"Dev seed complete: {len(users)} users, "
            f"{book_status_count} book statuses, {review_count} reviews, "
            f"{reading_session_count} reading sessions, {collection_count} collections"
        )


if __name__ == "__main__":
    asyncio.run(seed_dev_data())

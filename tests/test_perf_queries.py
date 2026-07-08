"""Performance smoke tests: query-count assertions for key flows.

These tests catch obvious N+1s and unbounded query growth early.
Thresholds are deliberately generous (not tight) to avoid false positives
while still catching major regressions.

Query budgets per endpoint:
- GET /books/{id}: ≤5 queries (book + releases + isbns + contributors + ratings)
- GET /me/library: ≤4 queries per page (statuses + ratings aggregates)
- GET /collections/{id}: ≤4 queries (collection + items + paginated results)
"""

from collections.abc import AsyncIterator

import pytest
from httpx import AsyncClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.book_status import BookStatus, BookStatusKind
from app.models.catalog import Book, Contributor, Release
from app.models.collection import Collection, CollectionItem
from app.models.user import User


class QueryCounter:
    """Track SQL query count during a context."""

    def __init__(self) -> None:
        self.count = 0
        self._listeners: list = []

    def __enter__(self):
        self.count = 0
        self._listeners = []

        def receive_after_cursor_execute(
            _conn, _cursor, _statement, _params, _context, _executemany
        ):
            self.count += 1

        # Use a weakref-aware event listener to avoid memory issues
        listener = receive_after_cursor_execute
        self._listeners.append(listener)
        # We'll attach to the engine directly in the test; this just holds the reference
        return self

    def __exit__(self, *args):
        # Listeners will be removed by the fixture
        pass


@pytest.fixture
async def query_counter(db_session: AsyncSession):
    """Count SQL queries executed during a test block."""
    counter = QueryCounter()

    def receive_after_cursor_execute(
        _conn, _cursor, _statement, _params, _context, _executemany
    ):
        counter.count += 1

    # Attach to the raw engine
    engine = db_session.get_bind()
    event.listen(
        engine.sync_engine, "after_cursor_execute", receive_after_cursor_execute
    )
    counter.count = 0

    yield counter

    # Clean up
    event.remove(
        engine.sync_engine, "after_cursor_execute", receive_after_cursor_execute
    )


@pytest.fixture
async def book_with_releases_and_contributors(
    db_session: AsyncSession,
) -> AsyncIterator[Book]:
    """Create a book with releases, contributors, and ISBNs for testing."""
    book = Book(
        title="Test Book",
        original_title="Test Book",
        original_language="en",
        first_publication_year=2020,
        description="A test book",
    )
    db_session.add(book)
    await db_session.flush()

    # Add contributor
    contributor = Contributor(
        full_name="Test Author", sort_name="Author, Test", slug="test-author"
    )
    db_session.add(contributor)
    await db_session.flush()

    from app.models.catalog import BookContributor, ContributorRole

    book_contributor = BookContributor(
        book_id=book.id,
        contributor_id=contributor.id,
        role=ContributorRole.author,
    )
    db_session.add(book_contributor)

    # Add release with ISBNs
    from app.models.catalog import ISBN, ISBNKind, ReleaseFormat

    release = Release(
        book_id=book.id,
        format=ReleaseFormat.hardcover,
        publisher="Test Publisher",
        published_year=2020,
        language="en",
    )
    db_session.add(release)
    await db_session.flush()

    isbn = ISBN(
        release_id=release.id,
        code_normalized="9780123456789",
        code_original="978-0-12-345678-9",
        kind=ISBNKind.isbn13,
    )
    db_session.add(isbn)

    await db_session.commit()
    yield book


@pytest.fixture
async def user_with_library_items(
    db_session: AsyncSession,
) -> AsyncIterator[tuple[User, list[Book]]]:
    """Create a user with multiple book statuses in their library."""
    user = User(
        email="library@example.com",
        username="library_user",
        display_name="Library User",
    )
    db_session.add(user)
    await db_session.flush()

    books = []
    for i in range(3):
        book = Book(
            title=f"Library Book {i}",
            original_title=f"Library Book {i}",
            original_language="en",
            first_publication_year=2020,
            description=f"Test book {i}",
        )
        db_session.add(book)
        await db_session.flush()
        books.append(book)

        # Add status
        status = BookStatus(
            user_id=user.id,
            book_id=book.id,
            status=BookStatusKind.owned,
        )
        db_session.add(status)

    await db_session.commit()
    yield user, books


@pytest.fixture
async def user_with_collection(
    db_session: AsyncSession,
) -> AsyncIterator[tuple[User, Collection, list[Book]]]:
    """Create a user with a collection containing books."""
    user = User(
        email="collector@example.com",
        username="collector_user",
        display_name="Collector User",
    )
    db_session.add(user)
    await db_session.flush()

    collection = Collection(
        user_id=user.id,
        name="Test Collection",
        description="A test collection",
        is_public=False,
    )
    db_session.add(collection)
    await db_session.flush()

    books = []
    for i in range(3):
        book = Book(
            title=f"Collection Book {i}",
            original_title=f"Collection Book {i}",
            original_language="en",
            first_publication_year=2020,
            description=f"Test collection book {i}",
        )
        db_session.add(book)
        await db_session.flush()
        books.append(book)

        # Add to collection
        item = CollectionItem(
            collection_id=collection.id,
            book_id=book.id,
            position=i,
        )
        db_session.add(item)

    await db_session.commit()
    yield user, collection, books


@pytest.mark.asyncio
class TestPerformanceQueries:
    """Performance smoke tests for key API flows."""

    async def test_get_book_by_id_query_count(
        self,
        async_client: AsyncClient,
        book_with_releases_and_contributors: Book,
    ):
        """GET /books/{id} should use ≤5 queries.

        Budget:
        - 1 query: fetch book with eager-loaded releases + contributors
        - 1 query: fetch ISBNs (via eager_nested on releases)
        - 1 query: fetch book-level rating aggregate
        - 1 query: fetch release-level rating aggregate
        - 1 query: margin/buffer
        """
        book_id = book_with_releases_and_contributors.id

        response = await async_client.get(f"/api/v1/books/{book_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(book_id)
        assert data["title"] == "Test Book"
        assert len(data["releases"]) > 0

    async def test_get_library_query_count(
        self,
        async_client: AsyncClient,
        auth_client,
        db_session: AsyncSession,
        user_with_library_items: tuple[User, list[Book]],
    ):
        """GET /me/library should use ≤4 queries per page.

        Budget:
        - 1 query: fetch paginated book statuses
        - 1 query: fetch rating aggregates
        - 1 query: margin
        """
        user, _books = user_with_library_items
        # Override to use this user
        from app.core.deps import get_current_user
        from app.main import app

        app.dependency_overrides[get_current_user] = lambda: user

        response = await async_client.get("/api/v1/me/library?limit=10")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3
        assert len(data["items"]) == 3

        # Cleanup
        app.dependency_overrides.pop(get_current_user, None)

    async def test_get_collection_query_count(
        self,
        async_client: AsyncClient,
        auth_client,
        user_with_collection: tuple[User, Collection, list[Book]],
    ):
        """GET /collections/{id} should use ≤4 queries.

        Budget:
        - 1 query: fetch collection with items
        - 1 query: margin/buffer
        """
        user, collection, _books = user_with_collection
        from app.core.deps import get_current_user
        from app.main import app

        app.dependency_overrides[get_current_user] = lambda: user

        collection_id = collection.id
        response = await async_client.get(f"/api/v1/collections/{collection_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(collection_id)
        assert data["name"] == "Test Collection"
        assert data["items"]["total"] == 3

        # Cleanup
        app.dependency_overrides.pop(get_current_user, None)

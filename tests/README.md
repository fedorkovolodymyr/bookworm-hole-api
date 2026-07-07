# Tests

## Test Structure

Tests are organized by feature/component following the app's module structure:

- `test_books_router.py` → tests for books router endpoints
- `test_users_router.py` → tests for users router endpoints
- Unit tests for services, repositories, models
- Integration tests in `integration/` subdirectory

## Test Fixtures

### pytest Fixtures (conftest.py)

- `db_session` — async database session with transactional rollback for each test
- `async_client` — AsyncClient fixture for testing HTTP endpoints
- `auth_client` — factory fixture for creating authenticated clients by role
- `admin_client` — pre-built admin-authenticated client
- `reader_client` — pre-built reader-authenticated client

### Polyfactory Model Factories

Factories for generating test model instances are in `tests/factories/`. Use these to quickly create valid test data:

```python
from tests.factories import UserFactory, BookFactory, ReviewFactory

def test_create_review(db_session: AsyncSession):
    # Create test data using factories
    user = UserFactory.create()
    book = BookFactory.create()
    review_data = ReviewFactory.create(user_id=user.id, book_id=book.id)

    # Test code...
```

Available factories:

- `UserFactory` → User instances (emails/usernames are unique-ish via Faker)
- `BookFactory` → Book instances
- `ReleaseFactory` → Release instances (book editions)
- `ISBNFactory` → ISBN instances
- `ContributorFactory` → Contributor instances (authors, illustrators, etc.)
- `CollectionFactory` → Collection instances
- `CollectionItemFactory` → CollectionItem instances
- `ReviewFactory` → Review instances
- `ReadingSessionFactory` → ReadingSession instances
- `FriendshipFactory` → Friendship instances

Factories are powered by `polyfactory` and auto-generate valid field values. Override any field by passing it to `.create()`:

```python
user = UserFactory.create(email="alice@example.com", username="alice", is_admin=True)
book = BookFactory.create(title="Custom Book Title")
```

## Test Conventions

### Structure

Each test file groups tests in classes by endpoint/unit under test:

```python
class TestCreateBook:
    """Tests for POST /books endpoint."""

    async def test_creates_book_with_valid_data(self, async_client):
        ...

    async def test_rejects_duplicate_title(self, async_client):
        ...
```

### Database Tests

Tests needing DB access use the `db_session` fixture with transactional rollback:

```python
async def test_book_repository_update(db_session: AsyncSession):
    book = await book_repository.create(session=db_session, data=BookSchema(...))
    # Changes auto-rollback after test
```

Override `get_session` in the test file for custom test isolation:

```python
@pytest.fixture
async def custom_session(db_session: AsyncSession):
    async def _get_session_override():
        yield db_session
    app.dependency_overrides[get_session] = _get_session_override
    yield db_session
```

### HTTP Tests

HTTP route tests use `async_client` or `auth_client`:

```python
async def test_get_book_returns_book(async_client: AsyncClient):
    response = await async_client.get("/books/123")
    assert response.status_code == 200

async def test_admin_only_endpoint(admin_client: AsyncClient):
    response = await admin_client.post("/admin/users")
    assert response.status_code in (200, 201)
```

### Coverage

Run `task test` to execute all tests with coverage. The test suite must maintain 80% line coverage (see `.coverage-baseline` and `pyproject.toml`).

## Seed Data

Two seed scripts populate test/dev databases:

- `task seed` → loads catalog data (books, releases, contributors)
- `task seed:dev` → loads dev users, collections, reviews, reading sessions (requires `task seed` first)
- `task seed:test` → loads minimal test fixtures (rarely needed; use factories instead)

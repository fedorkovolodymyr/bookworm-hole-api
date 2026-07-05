from collections.abc import AsyncIterator
from datetime import UTC, datetime

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.main import app
from app.models.catalog import ISBN, ISBNKind, Release, ReleaseFormat
from app.models.catalog import Book as BookModel
from app.models.review import Review
from app.models.user import User


def _login_as(user: User) -> None:
    app.dependency_overrides[get_current_user] = lambda: user


BookWithReleases = tuple[BookModel, ISBN, ISBN]


@pytest.fixture
async def book_with_releases(
    db_session: AsyncSession,
) -> BookWithReleases:
    book = BookModel(title="Dune", description="Desert planet epic")
    db_session.add(book)
    await db_session.flush()

    hardcover = Release(
        book_id=book.id,
        format=ReleaseFormat.hardcover,
        publisher="Chilton Books",
        language="en",
    )
    paperback = Release(
        book_id=book.id,
        format=ReleaseFormat.paperback,
        publisher="Ace Books",
        language="en",
    )
    db_session.add(hardcover)
    db_session.add(paperback)
    await db_session.flush()

    hardcover_isbn = ISBN(
        release_id=hardcover.id,
        code_normalized="9780441013593",
        code_original="0441013597",
        kind=ISBNKind.isbn13,
        created_at=datetime.now(UTC),
    )
    paperback_isbn = ISBN(
        release_id=paperback.id,
        code_normalized="9780143111580",
        code_original="9780143111580",
        kind=ISBNKind.isbn13,
        created_at=datetime.now(UTC),
    )
    db_session.add(hardcover_isbn)
    db_session.add(paperback_isbn)
    await db_session.commit()

    return book, hardcover_isbn, paperback_isbn


async def test_retrieve_book_by_isbn_dedup_and_shape(
    async_client: AsyncClient, book_with_releases: BookWithReleases
):
    book, hardcover_isbn, paperback_isbn = book_with_releases

    response_hc = await async_client.get(
        f"/api/v1/books/by-isbn/{hardcover_isbn.code_original}"
    )
    response_pb = await async_client.get(
        f"/api/v1/books/by-isbn/{paperback_isbn.code_original}"
    )

    assert response_hc.status_code == 200
    assert response_pb.status_code == 200
    data = response_hc.json()
    assert data["id"] == str(book.id)
    assert response_pb.json()["id"] == str(book.id)
    assert len(data["releases"]) == 2
    assert all(len(release["isbns"]) == 1 for release in data["releases"])


async def test_retrieve_book_by_isbn_not_found(async_client: AsyncClient):
    response = await async_client.get("/api/v1/books/by-isbn/9999999999999")
    assert response.status_code == 404


async def test_retrieve_book_by_isbn_invalid_input(async_client: AsyncClient):
    response = await async_client.get("/api/v1/books/by-isbn/not-an-isbn")
    assert response.status_code == 404


async def test_retrieve_book_by_id_includes_releases(
    async_client: AsyncClient, book_with_releases: BookWithReleases
):
    book, _, _ = book_with_releases

    response = await async_client.get(f"/api/v1/books/{book.id}")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(book.id)
    assert len(data["releases"]) == 2


async def test_retrieve_book_by_id_not_found(async_client: AsyncClient):
    response = await async_client.get(
        "/api/v1/books/00000000-0000-0000-0000-000000000000"
    )
    assert response.status_code == 404


async def test_retrieve_book_by_id_invalid_uuid(async_client: AsyncClient):
    response = await async_client.get("/api/v1/books/not-a-uuid")
    assert response.status_code == 422


async def test_retrieve_all_books_filters_by_title(
    async_client: AsyncClient, book_with_releases: BookWithReleases
):
    book, _, _ = book_with_releases

    response = await async_client.get("/api/v1/books/", params={"title": "Dune"})

    assert response.status_code == 200
    data = response.json()
    assert {"items", "total", "limit", "offset"} <= data.keys()
    assert any(item["id"] == str(book.id) for item in data["items"])


async def test_create_book_requires_admin(async_client: AsyncClient):
    response = await async_client.post(
        "/api/v1/books/",
        json={"title": "New Book", "description": "desc"},
    )
    assert response.status_code == 401


async def test_create_book_forbidden_for_non_admin(reader_client: AsyncClient):
    response = await reader_client.post(
        "/api/v1/books/",
        json={"title": "New Book", "description": "desc"},
    )
    assert response.status_code == 403


async def test_create_book_allowed_for_admin(admin_client: AsyncClient):
    response = await admin_client.post(
        "/api/v1/books/",
        json={"title": "New Book", "description": "desc"},
    )
    assert response.status_code == 201
    assert response.json()["title"] == "New Book"


async def test_create_book_missing_title_returns_422(admin_client: AsyncClient):
    response = await admin_client.post(
        "/api/v1/books/",
        json={"description": "desc"},
    )
    assert response.status_code == 422


async def test_modify_book_requires_admin(
    async_client: AsyncClient, book_with_releases: BookWithReleases
):
    book, _, _ = book_with_releases

    response = await async_client.patch(
        f"/api/v1/books/{book.id}", json={"title": "Renamed"}
    )
    assert response.status_code == 401


async def test_modify_book_forbidden_for_non_admin(
    reader_client: AsyncClient, book_with_releases: BookWithReleases
):
    book, _, _ = book_with_releases

    response = await reader_client.patch(
        f"/api/v1/books/{book.id}", json={"title": "Renamed"}
    )
    assert response.status_code == 403


async def test_modify_book_not_found(admin_client: AsyncClient):
    response = await admin_client.patch(
        "/api/v1/books/00000000-0000-0000-0000-000000000000",
        json={"title": "Renamed"},
    )
    assert response.status_code == 404


async def test_modify_book_allowed_for_admin(
    admin_client: AsyncClient, book_with_releases: BookWithReleases
):
    book, _, _ = book_with_releases

    response = await admin_client.patch(
        f"/api/v1/books/{book.id}", json={"title": "Renamed"}
    )
    assert response.status_code == 200
    assert response.json()["title"] == "Renamed"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("title", "New Title"),
        ("original_title", "Original"),
        ("original_language", "fr"),
        ("first_publication_year", 1965),
        ("description", "New description"),
    ],
)
async def test_modify_book_updates_each_field(
    admin_client: AsyncClient,
    book_with_releases: BookWithReleases,
    field: str,
    value: object,
):
    book, _, _ = book_with_releases

    response = await admin_client.patch(f"/api/v1/books/{book.id}", json={field: value})
    assert response.status_code == 200
    data = response.json()
    original = {
        "title": book.title,
        "original_title": book.original_title,
        "original_language": book.original_language,
        "first_publication_year": book.first_publication_year,
        "description": book.description,
    }
    for name, original_value in original.items():
        assert data[name] == (value if name == field else original_value)


async def test_delete_book_requires_admin(
    async_client: AsyncClient, book_with_releases: BookWithReleases
):
    book, _, _ = book_with_releases

    response = await async_client.delete(f"/api/v1/books/{book.id}")
    assert response.status_code == 401


async def test_delete_book_forbidden_for_non_admin(
    reader_client: AsyncClient, book_with_releases: BookWithReleases
):
    book, _, _ = book_with_releases

    response = await reader_client.delete(f"/api/v1/books/{book.id}")
    assert response.status_code == 403


async def test_delete_book_not_found(admin_client: AsyncClient):
    response = await admin_client.delete(
        "/api/v1/books/00000000-0000-0000-0000-000000000000"
    )
    assert response.status_code == 404


async def test_delete_book_allowed_for_admin(
    admin_client: AsyncClient, book_with_releases: BookWithReleases
):
    book, _, _ = book_with_releases

    response = await admin_client.delete(f"/api/v1/books/{book.id}")
    assert response.status_code == 204


@pytest.fixture
async def user(db_session: AsyncSession) -> AsyncIterator[User]:
    user = User(email="user@example.com", username="user", display_name="User")
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    _login_as(user)
    yield user
    app.dependency_overrides.pop(get_current_user, None)


class TestRatingAggregates:
    async def test_book_rating_aggregates_with_mixed_reviews(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        user: User,
    ):
        book = BookModel(title="Test Book", description="Test description")
        db_session.add(book)
        await db_session.flush()

        release1 = Release(
            book_id=book.id,
            format=ReleaseFormat.hardcover,
            publisher="Publisher 1",
            language="en",
        )
        release2 = Release(
            book_id=book.id,
            format=ReleaseFormat.paperback,
            publisher="Publisher 2",
            language="en",
        )
        db_session.add(release1)
        db_session.add(release2)
        await db_session.flush()

        book_review = Review(user_id=user.id, book_id=book.id, rating=5, is_public=True)
        release1_review = Review(
            user_id=user.id, release_id=release1.id, rating=4, is_public=True
        )
        release2_review = Review(
            user_id=user.id, release_id=release2.id, rating=3, is_public=True
        )
        private_review = Review(
            user_id=user.id, book_id=book.id, rating=1, is_public=False
        )
        db_session.add_all(
            [book_review, release1_review, release2_review, private_review]
        )
        await db_session.commit()

        response = await async_client.get(f"/api/v1/books/{book.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["average_rating"] == 4.0
        assert data["rating_count"] == 3

    async def test_book_rating_aggregates_no_reviews(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
    ):
        book = BookModel(title="Unreviewed Book", description="No reviews yet")
        db_session.add(book)
        await db_session.commit()

        response = await async_client.get(f"/api/v1/books/{book.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["average_rating"] is None
        assert data["rating_count"] == 0

    async def test_release_rating_aggregates(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        user: User,
    ):
        book = BookModel(title="Test Book", description="Test description")
        db_session.add(book)
        await db_session.flush()

        release = Release(
            book_id=book.id,
            format=ReleaseFormat.hardcover,
            publisher="Publisher",
            language="en",
        )
        db_session.add(release)
        await db_session.flush()

        review1 = Review(
            user_id=user.id, release_id=release.id, rating=5, is_public=True
        )
        review2 = Review(
            user_id=user.id,
            release_id=release.id,
            rating=3,
            is_public=True,
        )
        db_session.add_all([review1, review2])
        await db_session.commit()

        response = await async_client.get(f"/api/v1/releases/{release.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["average_rating"] == 4.0
        assert data["rating_count"] == 2

    async def test_release_rating_aggregates_excludes_book_reviews(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        user: User,
    ):
        book = BookModel(title="Test Book", description="Test description")
        db_session.add(book)
        await db_session.flush()

        release = Release(
            book_id=book.id,
            format=ReleaseFormat.hardcover,
            publisher="Publisher",
            language="en",
        )
        db_session.add(release)
        await db_session.flush()

        book_review = Review(user_id=user.id, book_id=book.id, rating=5, is_public=True)
        release_review = Review(
            user_id=user.id, release_id=release.id, rating=3, is_public=True
        )
        db_session.add_all([book_review, release_review])
        await db_session.commit()

        response = await async_client.get(f"/api/v1/releases/{release.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["average_rating"] == 3.0
        assert data["rating_count"] == 1

    async def test_release_rating_aggregates_no_reviews(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
    ):
        book = BookModel(title="Test Book", description="Test description")
        db_session.add(book)
        await db_session.flush()

        release = Release(
            book_id=book.id,
            format=ReleaseFormat.hardcover,
            publisher="Publisher",
            language="en",
        )
        db_session.add(release)
        await db_session.commit()

        response = await async_client.get(f"/api/v1/releases/{release.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["average_rating"] is None
        assert data["rating_count"] == 0

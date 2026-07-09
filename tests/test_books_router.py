from collections.abc import AsyncIterator
from datetime import UTC, datetime

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.main import app
from app.models.book_status import BookStatus, BookStatusKind
from app.models.catalog import (
    ISBN,
    ISBNKind,
    Release,
    ReleaseFormat,
)
from app.models.catalog import Book as BookModel
from app.models.catalog import Contributor as ContributorModel
from app.models.collection import Collection, CollectionItem
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


async def test_retrieve_all_books_rejects_limit_above_cap(async_client: AsyncClient):
    response = await async_client.get("/api/v1/books/", params={"limit": 101})
    assert response.status_code == 422


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


@pytest.fixture
async def other_user(db_session: AsyncSession) -> User:
    other_user = User(
        email="other-user@example.com", username="other-user", display_name="Other"
    )
    db_session.add(other_user)
    await db_session.commit()
    await db_session.refresh(other_user)
    return other_user


class TestRatingAggregates:
    async def test_book_rating_aggregates_with_mixed_reviews(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        user: User,
        other_user: User,
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
            user_id=other_user.id, book_id=book.id, rating=1, is_public=False
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
        other_user: User,
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
            user_id=other_user.id,
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


@pytest.fixture
async def source_and_target_books(
    db_session: AsyncSession,
) -> tuple[BookModel, BookModel]:
    source = BookModel(title="Dune (dup)", description="Duplicate entry")
    target = BookModel(title="Dune", description="Canonical entry")
    db_session.add(source)
    db_session.add(target)
    await db_session.commit()
    await db_session.refresh(source)
    await db_session.refresh(target)
    return source, target


@pytest.fixture
async def merge_user(db_session: AsyncSession) -> User:
    user = User(email="merger@example.com", username="merger", display_name="Merger")
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


class TestMergeBook:
    async def test_merge_book_requires_admin(
        self,
        async_client: AsyncClient,
        source_and_target_books: tuple[BookModel, BookModel],
    ):
        source, target = source_and_target_books

        response = await async_client.post(
            f"/api/v1/books/{source.id}/merge-into/{target.id}"
        )
        assert response.status_code == 401

    async def test_merge_book_forbidden_for_non_admin(
        self,
        reader_client: AsyncClient,
        source_and_target_books: tuple[BookModel, BookModel],
    ):
        source, target = source_and_target_books

        response = await reader_client.post(
            f"/api/v1/books/{source.id}/merge-into/{target.id}"
        )
        assert response.status_code == 403

    async def test_merge_book_source_not_found(
        self,
        admin_client: AsyncClient,
        source_and_target_books: tuple[BookModel, BookModel],
    ):
        _, target = source_and_target_books

        response = await admin_client.post(
            f"/api/v1/books/00000000-0000-0000-0000-000000000000/merge-into/{target.id}"
        )
        assert response.status_code == 404

    async def test_merge_book_target_not_found(
        self,
        admin_client: AsyncClient,
        source_and_target_books: tuple[BookModel, BookModel],
    ):
        source, _ = source_and_target_books

        response = await admin_client.post(
            f"/api/v1/books/{source.id}/merge-into/00000000-0000-0000-0000-000000000000"
        )
        assert response.status_code == 404

    async def test_merge_book_into_itself_is_conflict(
        self,
        admin_client: AsyncClient,
        source_and_target_books: tuple[BookModel, BookModel],
    ):
        source, _ = source_and_target_books

        response = await admin_client.post(
            f"/api/v1/books/{source.id}/merge-into/{source.id}"
        )
        assert response.status_code == 409

    async def test_merge_book_reassigns_releases_and_deletes_source(
        self,
        admin_client: AsyncClient,
        db_session: AsyncSession,
        source_and_target_books: tuple[BookModel, BookModel],
    ):
        source, target = source_and_target_books
        release = Release(
            book_id=source.id,
            format=ReleaseFormat.paperback,
            publisher="Ace Books",
            language="en",
        )
        db_session.add(release)
        await db_session.commit()
        await db_session.refresh(release)

        response = await admin_client.post(
            f"/api/v1/books/{source.id}/merge-into/{target.id}"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(target.id)
        assert any(r["id"] == str(release.id) for r in data["releases"])

        assert await db_session.get(BookModel, source.id) is None
        moved_release = await db_session.get(Release, release.id)
        assert moved_release is not None
        assert moved_release.book_id == target.id

    async def test_merge_book_reassigns_reviews_statuses_and_collection_items(
        self,
        admin_client: AsyncClient,
        db_session: AsyncSession,
        source_and_target_books: tuple[BookModel, BookModel],
        merge_user: User,
    ):
        source, target = source_and_target_books
        review = Review(user_id=merge_user.id, book_id=source.id, rating=4)
        book_status = BookStatus(
            user_id=merge_user.id, book_id=source.id, status=BookStatusKind.owned
        )
        collection = Collection(user_id=merge_user.id, name="My Collection")
        db_session.add(review)
        db_session.add(book_status)
        db_session.add(collection)
        await db_session.commit()
        await db_session.refresh(collection)
        item = CollectionItem(collection_id=collection.id, book_id=source.id)
        db_session.add(item)
        await db_session.commit()
        await db_session.refresh(review)
        await db_session.refresh(book_status)
        await db_session.refresh(item)

        response = await admin_client.post(
            f"/api/v1/books/{source.id}/merge-into/{target.id}"
        )
        assert response.status_code == 200

        moved_review = await db_session.get(Review, review.id)
        moved_status = await db_session.get(BookStatus, book_status.id)
        moved_item = await db_session.get(CollectionItem, item.id)
        assert moved_review is not None
        assert moved_review.book_id == target.id
        assert moved_status is not None
        assert moved_status.book_id == target.id
        assert moved_item is not None
        assert moved_item.book_id == target.id

    async def test_merge_book_drops_conflicting_duplicate_review(
        self,
        admin_client: AsyncClient,
        db_session: AsyncSession,
        source_and_target_books: tuple[BookModel, BookModel],
        merge_user: User,
    ):
        source, target = source_and_target_books
        source_review = Review(
            user_id=merge_user.id, book_id=source.id, rating=2, title="On the dup"
        )
        target_review = Review(
            user_id=merge_user.id, book_id=target.id, rating=5, title="On the original"
        )
        db_session.add(source_review)
        db_session.add(target_review)
        await db_session.commit()
        await db_session.refresh(source_review)
        await db_session.refresh(target_review)

        response = await admin_client.post(
            f"/api/v1/books/{source.id}/merge-into/{target.id}"
        )
        assert response.status_code == 200

        assert await db_session.get(Review, source_review.id) is None
        remaining = await db_session.get(Review, target_review.id)
        assert remaining is not None
        assert remaining.title == "On the original"
        result = await db_session.execute(
            select(Review).where(Review.book_id == target.id)
        )
        assert len(result.scalars().all()) == 1


class TestBookContributors:
    async def test_add_contributor_requires_admin(
        self, async_client: AsyncClient, book_with_releases: BookWithReleases
    ):
        book, _, _ = book_with_releases
        response = await async_client.post(
            f"/api/v1/books/{book.id}/contributors",
            json={
                "contributor_id": "00000000-0000-0000-0000-000000000000",
                "role": "author",
            },
        )
        assert response.status_code == 401

    async def test_add_contributor_forbidden_for_non_admin(
        self, reader_client: AsyncClient, book_with_releases: BookWithReleases
    ):
        book, _, _ = book_with_releases
        response = await reader_client.post(
            f"/api/v1/books/{book.id}/contributors",
            json={
                "contributor_id": "00000000-0000-0000-0000-000000000000",
                "role": "author",
            },
        )
        assert response.status_code == 403

    async def test_add_contributor_book_not_found(self, admin_client: AsyncClient):
        response = await admin_client.post(
            "/api/v1/books/00000000-0000-0000-0000-000000000000/contributors",
            json={
                "contributor_id": "00000000-0000-0000-0000-000000000000",
                "role": "author",
            },
        )
        assert response.status_code == 404

    async def test_add_contributor_contributor_not_found(
        self, admin_client: AsyncClient, book_with_releases: BookWithReleases
    ):
        book, _, _ = book_with_releases
        response = await admin_client.post(
            f"/api/v1/books/{book.id}/contributors",
            json={
                "contributor_id": "00000000-0000-0000-0000-000000000000",
                "role": "author",
            },
        )
        assert response.status_code == 404

    async def test_add_contributor_success(
        self,
        admin_client: AsyncClient,
        db_session: AsyncSession,
        book_with_releases: BookWithReleases,
    ):
        book, _, _ = book_with_releases
        contributor = ContributorModel(
            full_name="Frank Herbert",
            sort_name="Herbert, Frank",
            slug="frank-herbert",
        )
        db_session.add(contributor)
        await db_session.commit()
        await db_session.refresh(contributor)

        response = await admin_client.post(
            f"/api/v1/books/{book.id}/contributors",
            json={"contributor_id": str(contributor.id), "role": "author"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "created"

    async def test_add_contributor_idempotent(
        self,
        admin_client: AsyncClient,
        db_session: AsyncSession,
        book_with_releases: BookWithReleases,
    ):
        book, _, _ = book_with_releases
        contributor = ContributorModel(
            full_name="Frank Herbert",
            sort_name="Herbert, Frank",
            slug="frank-herbert",
        )
        db_session.add(contributor)
        await db_session.commit()
        await db_session.refresh(contributor)

        response1 = await admin_client.post(
            f"/api/v1/books/{book.id}/contributors",
            json={"contributor_id": str(contributor.id), "role": "author"},
        )
        assert response1.status_code == 200
        assert response1.json()["status"] == "created"

        response2 = await admin_client.post(
            f"/api/v1/books/{book.id}/contributors",
            json={"contributor_id": str(contributor.id), "role": "author"},
        )
        assert response2.status_code == 200
        assert response2.json()["status"] == "already_existed"

    async def test_remove_contributor_success(
        self,
        admin_client: AsyncClient,
        db_session: AsyncSession,
        book_with_releases: BookWithReleases,
    ):
        book, _, _ = book_with_releases
        contributor = ContributorModel(
            full_name="Frank Herbert",
            sort_name="Herbert, Frank",
            slug="frank-herbert",
        )
        db_session.add(contributor)
        await db_session.commit()
        await db_session.refresh(contributor)

        await admin_client.post(
            f"/api/v1/books/{book.id}/contributors",
            json={"contributor_id": str(contributor.id), "role": "author"},
        )

        response = await admin_client.delete(
            f"/api/v1/books/{book.id}/contributors/{contributor.id}?role=author"
        )

        assert response.status_code == 204

    async def test_remove_contributor_not_found(
        self, admin_client: AsyncClient, book_with_releases: BookWithReleases
    ):
        book, _, _ = book_with_releases
        response = await admin_client.delete(
            f"/api/v1/books/{book.id}/contributors/00000000-0000-0000-0000-000000000000?role=author"
        )
        assert response.status_code == 404

from collections.abc import AsyncIterator

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.main import app
from app.models.catalog import Book as BookModel
from app.models.catalog import Release as ReleaseModel
from app.models.catalog import ReleaseFormat
from app.models.review import Review
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
async def book(db_session: AsyncSession) -> BookModel:
    book = BookModel(title="Dune", description="Desert planet epic")
    db_session.add(book)
    await db_session.commit()
    await db_session.refresh(book)
    return book


@pytest.fixture
async def release(db_session: AsyncSession, book: BookModel) -> ReleaseModel:
    release = ReleaseModel(
        book_id=book.id,
        format=ReleaseFormat.hardcover,
        publisher="Ace Books",
        language="en",
    )
    db_session.add(release)
    await db_session.commit()
    await db_session.refresh(release)
    return release


@pytest.fixture
async def review(db_session: AsyncSession, owner: User, book: BookModel) -> Review:
    review = Review(user_id=owner.id, book_id=book.id, rating=5, body="Great book")
    db_session.add(review)
    await db_session.commit()
    await db_session.refresh(review)
    return review


class TestCreateReview:
    async def test_requires_auth(self, async_client: AsyncClient, book: BookModel):
        response = await async_client.post(
            "/api/v1/reviews/", json={"book_id": str(book.id)}
        )
        assert response.status_code == 401

    async def test_creates_review_for_book(
        self, async_client: AsyncClient, owner: User, book: BookModel
    ):
        response = await async_client.post(
            "/api/v1/reviews/",
            json={"book_id": str(book.id), "rating": 4, "body": "Solid"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["user_id"] == str(owner.id)
        assert data["book_id"] == str(book.id)
        assert data["release_id"] is None
        assert data["rating"] == 4
        assert data["body"] == "Solid"
        assert data["is_public"] is True
        assert data["contains_spoilers"] is False

    async def test_creates_review_for_release(
        self, async_client: AsyncClient, owner: User, release: ReleaseModel
    ):
        response = await async_client.post(
            "/api/v1/reviews/", json={"release_id": str(release.id)}
        )
        assert response.status_code == 201
        data = response.json()
        assert data["release_id"] == str(release.id)
        assert data["book_id"] is None
        assert data["rating"] is None
        assert data["body"] is None

    async def test_requires_exactly_one_target(
        self, async_client: AsyncClient, owner: User
    ):
        response = await async_client.post("/api/v1/reviews/", json={})
        assert response.status_code == 422

    async def test_rejects_both_targets(
        self,
        async_client: AsyncClient,
        owner: User,
        book: BookModel,
        release: ReleaseModel,
    ):
        response = await async_client.post(
            "/api/v1/reviews/",
            json={"book_id": str(book.id), "release_id": str(release.id)},
        )
        assert response.status_code == 422

    async def test_rejects_out_of_range_rating(
        self, async_client: AsyncClient, owner: User, book: BookModel
    ):
        response = await async_client.post(
            "/api/v1/reviews/", json={"book_id": str(book.id), "rating": 6}
        )
        assert response.status_code == 422

    async def test_rejects_duplicate_review_for_same_book(
        self, async_client: AsyncClient, owner: User, book: BookModel, review: Review
    ):
        response = await async_client.post(
            "/api/v1/reviews/", json={"book_id": str(book.id)}
        )
        assert response.status_code == 409


class TestRetrieveReview:
    async def test_owner_can_view_private(
        self, async_client: AsyncClient, owner: User, book: BookModel
    ):
        create = await async_client.post(
            "/api/v1/reviews/", json={"book_id": str(book.id), "is_public": False}
        )
        review_id = create.json()["id"]

        response = await async_client.get(f"/api/v1/reviews/{review_id}")
        assert response.status_code == 200
        assert response.json()["id"] == review_id

    async def test_non_owner_cannot_view_private(
        self,
        async_client: AsyncClient,
        owner: User,
        other: User,
        book: BookModel,
    ):
        create = await async_client.post(
            "/api/v1/reviews/", json={"book_id": str(book.id), "is_public": False}
        )
        review_id = create.json()["id"]

        _login_as(other)
        response = await async_client.get(f"/api/v1/reviews/{review_id}")
        assert response.status_code == 404

    async def test_anyone_can_view_public(
        self,
        async_client: AsyncClient,
        owner: User,
        other: User,
        review: Review,
    ):
        _login_as(other)
        response = await async_client.get(f"/api/v1/reviews/{review.id}")
        assert response.status_code == 200

    async def test_not_found(self, async_client: AsyncClient, owner: User):
        response = await async_client.get(
            "/api/v1/reviews/00000000-0000-0000-0000-000000000000"
        )
        assert response.status_code == 404


class TestUpdateReview:
    @pytest.mark.parametrize(
        ("field", "value"),
        [
            ("rating", 2),
            ("title", "Updated title"),
            ("body", "Updated body"),
            ("is_public", False),
            ("contains_spoilers", True),
        ],
    )
    async def test_updates_each_field(
        self,
        async_client: AsyncClient,
        owner: User,
        review: Review,
        field: str,
        value: object,
    ):
        response = await async_client.patch(
            f"/api/v1/reviews/{review.id}", json={field: value}
        )
        assert response.status_code == 200
        data = response.json()
        original = {
            "rating": review.rating,
            "title": review.title,
            "body": review.body,
            "is_public": review.is_public,
            "contains_spoilers": review.contains_spoilers,
        }
        for name, original_value in original.items():
            assert data[name] == (value if name == field else original_value)

    async def test_not_found_for_non_owner(
        self, async_client: AsyncClient, owner: User, other: User, review: Review
    ):
        _login_as(other)
        response = await async_client.patch(
            f"/api/v1/reviews/{review.id}", json={"title": "Hijacked"}
        )
        assert response.status_code == 404

    async def test_requires_auth(
        self, async_client: AsyncClient, owner: User, review: Review
    ):
        app.dependency_overrides.pop(get_current_user, None)
        response = await async_client.patch(
            f"/api/v1/reviews/{review.id}", json={"title": "Hijacked"}
        )
        assert response.status_code == 401


class TestDeleteReview:
    async def test_deletes_review(
        self, async_client: AsyncClient, owner: User, review: Review
    ):
        response = await async_client.delete(f"/api/v1/reviews/{review.id}")
        assert response.status_code == 204

        follow_up = await async_client.get(f"/api/v1/reviews/{review.id}")
        assert follow_up.status_code == 404

    async def test_not_found_for_non_owner(
        self, async_client: AsyncClient, owner: User, other: User, review: Review
    ):
        _login_as(other)
        response = await async_client.delete(f"/api/v1/reviews/{review.id}")
        assert response.status_code == 404

    async def test_not_found(self, async_client: AsyncClient, owner: User):
        response = await async_client.delete(
            "/api/v1/reviews/00000000-0000-0000-0000-000000000000"
        )
        assert response.status_code == 404


class TestListBookReviews:
    async def test_lists_public_reviews_for_book(
        self, async_client: AsyncClient, owner: User, book: BookModel, review: Review
    ):
        response = await async_client.get(f"/api/v1/books/{book.id}/reviews")
        assert response.status_code == 200
        data = response.json()
        assert {item["id"] for item in data["items"]} == {str(review.id)}
        assert data["total"] == 1

    async def test_sorts_by_rating(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        owner: User,
        other: User,
        book: BookModel,
        review: Review,
    ):
        second = Review(user_id=other.id, book_id=book.id, rating=1)
        db_session.add(second)
        await db_session.commit()
        await db_session.refresh(second)

        response = await async_client.get(
            f"/api/v1/books/{book.id}/reviews", params={"sort": "rating"}
        )
        assert response.status_code == 200
        ordered_ids = [item["id"] for item in response.json()["items"]]
        assert ordered_ids == [str(review.id), str(second.id)]

    async def test_excludes_private_reviews(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        owner: User,
        other: User,
        book: BookModel,
        review: Review,
    ):
        private = Review(user_id=other.id, book_id=book.id, is_public=False, rating=1)
        db_session.add(private)
        await db_session.commit()

        response = await async_client.get(f"/api/v1/books/{book.id}/reviews")
        assert response.status_code == 200
        data = response.json()
        assert {item["id"] for item in data["items"]} == {str(review.id)}
        assert data["total"] == 1


class TestListReleaseReviews:
    async def test_lists_reviews_for_release(
        self,
        async_client: AsyncClient,
        owner: User,
        release: ReleaseModel,
    ):
        create = await async_client.post(
            "/api/v1/reviews/", json={"release_id": str(release.id)}
        )
        review_id = create.json()["id"]

        response = await async_client.get(f"/api/v1/releases/{release.id}/reviews")
        assert response.status_code == 200
        data = response.json()
        assert {item["id"] for item in data["items"]} == {review_id}


class TestListUserReviews:
    async def test_lists_only_public_reviews(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        owner: User,
        book: BookModel,
        release: ReleaseModel,
        review: Review,
    ):
        private = Review(
            user_id=owner.id, release_id=release.id, is_public=False, rating=3
        )
        db_session.add(private)
        await db_session.commit()
        await db_session.refresh(private)

        response = await async_client.get(f"/api/v1/users/{owner.id}/reviews")
        assert response.status_code == 200
        data = response.json()
        assert {item["id"] for item in data["items"]} == {str(review.id)}

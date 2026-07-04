import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.catalog import Book as BookModel
from app.models.catalog import Release, ReleaseFormat


@pytest.fixture
async def book_with_release(db_session: AsyncSession) -> tuple[BookModel, Release]:
    book = BookModel(title="Dune", description="Desert planet epic")
    db_session.add(book)
    await db_session.flush()

    release = Release(
        book_id=book.id,
        format=ReleaseFormat.hardcover,
        publisher="Chilton Books",
        language="en",
    )
    db_session.add(release)
    await db_session.commit()

    return book, release


class TestRetrieveReleaseById:
    async def test_success(
        self,
        async_client: AsyncClient,
        book_with_release: tuple[BookModel, Release],
    ):
        _, release = book_with_release

        response = await async_client.get(f"/api/v1/releases/{release.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(release.id)
        assert data["isbns"] == []

    async def test_not_found(self, async_client: AsyncClient):
        response = await async_client.get(
            "/api/v1/releases/00000000-0000-0000-0000-000000000000"
        )
        assert response.status_code == 404

    async def test_invalid_uuid_returns_422(self, async_client: AsyncClient):
        response = await async_client.get("/api/v1/releases/not-a-uuid")
        assert response.status_code == 422


class TestCreateRelease:
    async def test_success(
        self,
        admin_client: AsyncClient,
        book_with_release: tuple[BookModel, Release],
    ):
        book, _ = book_with_release

        response = await admin_client.post(
            "/api/v1/releases/",
            json={
                "book_id": str(book.id),
                "format": "paperback",
                "publisher": "Ace Books",
                "language": "en",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["publisher"] == "Ace Books"

    async def test_book_not_found(self, admin_client: AsyncClient):
        response = await admin_client.post(
            "/api/v1/releases/",
            json={
                "book_id": "00000000-0000-0000-0000-000000000000",
                "format": "paperback",
                "publisher": "Ace Books",
                "language": "en",
            },
        )
        assert response.status_code == 404

    async def test_missing_format_returns_422(self, admin_client: AsyncClient):
        response = await admin_client.post(
            "/api/v1/releases/",
            json={
                "book_id": "00000000-0000-0000-0000-000000000000",
                "publisher": "Ace Books",
                "language": "en",
            },
        )
        assert response.status_code == 422

    async def test_requires_admin(self, async_client: AsyncClient):
        response = await async_client.post(
            "/api/v1/releases/",
            json={
                "book_id": "00000000-0000-0000-0000-000000000000",
                "format": "paperback",
                "publisher": "Ace Books",
                "language": "en",
            },
        )
        assert response.status_code == 401

    async def test_forbidden_for_non_admin(self, reader_client: AsyncClient):
        response = await reader_client.post(
            "/api/v1/releases/",
            json={
                "book_id": "00000000-0000-0000-0000-000000000000",
                "format": "paperback",
                "publisher": "Ace Books",
                "language": "en",
            },
        )
        assert response.status_code == 403


class TestModifyRelease:
    async def test_success(
        self,
        admin_client: AsyncClient,
        book_with_release: tuple[BookModel, Release],
    ):
        _, release = book_with_release

        response = await admin_client.patch(
            f"/api/v1/releases/{release.id}", json={"publisher": "New Publisher"}
        )

        assert response.status_code == 200
        assert response.json()["publisher"] == "New Publisher"

    async def test_not_found(self, admin_client: AsyncClient):
        response = await admin_client.patch(
            "/api/v1/releases/00000000-0000-0000-0000-000000000000",
            json={"publisher": "New Publisher"},
        )
        assert response.status_code == 404

    async def test_requires_admin(self, async_client: AsyncClient):
        response = await async_client.patch(
            "/api/v1/releases/00000000-0000-0000-0000-000000000000",
            json={"publisher": "New Publisher"},
        )
        assert response.status_code == 401

    async def test_forbidden_for_non_admin(self, reader_client: AsyncClient):
        response = await reader_client.patch(
            "/api/v1/releases/00000000-0000-0000-0000-000000000000",
            json={"publisher": "New Publisher"},
        )
        assert response.status_code == 403

    @pytest.mark.parametrize(
        ("field", "value"),
        [
            ("format", "paperback"),
            ("publisher", "New Publisher"),
            ("published_year", 1965),
            ("language", "fr"),
            ("page_count", 412),
            ("duration_minutes", 620),
            ("cover_image_url", "https://example.com/cover.jpg"),
            ("description_override", "Alt description"),
        ],
    )
    async def test_updates_each_field(
        self,
        admin_client: AsyncClient,
        book_with_release: tuple[BookModel, Release],
        field: str,
        value: object,
    ):
        _, release = book_with_release

        response = await admin_client.patch(
            f"/api/v1/releases/{release.id}", json={field: value}
        )

        assert response.status_code == 200
        data = response.json()
        original = {
            "format": release.format.value,
            "publisher": release.publisher,
            "published_year": release.published_year,
            "language": release.language,
            "page_count": release.page_count,
            "duration_minutes": release.duration_minutes,
            "cover_image_url": release.cover_image_url,
            "description_override": release.description_override,
        }
        for name, original_value in original.items():
            assert data[name] == (value if name == field else original_value)

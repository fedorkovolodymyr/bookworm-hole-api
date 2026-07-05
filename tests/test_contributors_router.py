import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.catalog import Book as BookModel
from app.models.catalog import (
    BookContributor,
    ContributorRole,
    ReleaseContributor,
    ReleaseFormat,
)
from app.models.catalog import Contributor as ContributorModel
from app.models.catalog import Release as ReleaseModel


@pytest.fixture
async def contributor(db_session: AsyncSession) -> ContributorModel:
    contributor = ContributorModel(
        full_name="Frank Herbert",
        sort_name="Herbert, Frank",
        slug="frank-herbert",
    )
    db_session.add(contributor)
    await db_session.commit()
    await db_session.refresh(contributor)
    return contributor


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
        format=ReleaseFormat.audiobook,
        publisher="Macmillan Audio",
        language="en",
    )
    db_session.add(release)
    await db_session.commit()
    await db_session.refresh(release)
    return release


@pytest.fixture
async def book_contribution(
    db_session: AsyncSession, contributor: ContributorModel, book: BookModel
) -> BookContributor:
    link = BookContributor(
        book_id=book.id,
        contributor_id=contributor.id,
        role=ContributorRole.author,
    )
    db_session.add(link)
    await db_session.commit()
    return link


@pytest.fixture
async def release_contribution(
    db_session: AsyncSession, contributor: ContributorModel, release: ReleaseModel
) -> ReleaseContributor:
    link = ReleaseContributor(
        release_id=release.id,
        contributor_id=contributor.id,
        role=ContributorRole.narrator,
    )
    db_session.add(link)
    await db_session.commit()
    return link


class TestRetrieveAllContributors:
    async def test_returns_paginated_shape(
        self, async_client: AsyncClient, contributor: ContributorModel
    ):
        response = await async_client.get("/api/v1/contributors/")

        assert response.status_code == 200
        data = response.json()
        assert {"items", "total", "limit", "offset"} <= data.keys()
        assert any(item["id"] == str(contributor.id) for item in data["items"])

    async def test_filters_by_name_matches_full_name(
        self, async_client: AsyncClient, contributor: ContributorModel
    ):
        response = await async_client.get(
            "/api/v1/contributors/", params={"name": "Frank"}
        )

        assert response.status_code == 200
        data = response.json()
        assert [item["id"] for item in data["items"]] == [str(contributor.id)]

    async def test_filters_by_name_matches_sort_name(
        self, async_client: AsyncClient, contributor: ContributorModel
    ):
        response = await async_client.get(
            "/api/v1/contributors/", params={"name": "Herbert,"}
        )

        assert response.status_code == 200
        data = response.json()
        assert [item["id"] for item in data["items"]] == [str(contributor.id)]

    async def test_filters_by_name_no_match(
        self, async_client: AsyncClient, contributor: ContributorModel
    ):
        response = await async_client.get(
            "/api/v1/contributors/", params={"name": "Nobody"}
        )

        assert response.status_code == 200
        assert response.json()["items"] == []

    async def test_filters_by_role(
        self,
        async_client: AsyncClient,
        contributor: ContributorModel,
        book_contribution: BookContributor,
    ):
        response = await async_client.get(
            "/api/v1/contributors/", params={"role": "author"}
        )

        assert response.status_code == 200
        data = response.json()
        assert [item["id"] for item in data["items"]] == [str(contributor.id)]

    async def test_filters_by_role_no_match(
        self,
        async_client: AsyncClient,
        contributor: ContributorModel,
        book_contribution: BookContributor,
    ):
        response = await async_client.get(
            "/api/v1/contributors/", params={"role": "translator"}
        )

        assert response.status_code == 200
        assert response.json()["items"] == []


class TestCreateContributor:
    async def test_requires_auth(self, async_client: AsyncClient):
        response = await async_client.post(
            "/api/v1/contributors/",
            json={"full_name": "Ursula K. Le Guin", "sort_name": "Le Guin, Ursula K."},
        )
        assert response.status_code == 401

    async def test_forbidden_for_non_admin(self, reader_client: AsyncClient):
        response = await reader_client.post(
            "/api/v1/contributors/",
            json={"full_name": "Ursula K. Le Guin", "sort_name": "Le Guin, Ursula K."},
        )
        assert response.status_code == 403

    async def test_allowed_for_admin(self, admin_client: AsyncClient):
        response = await admin_client.post(
            "/api/v1/contributors/",
            json={
                "full_name": "Ursula K. Le Guin",
                "sort_name": "Le Guin, Ursula K.",
                "birth_year": 1929,
                "death_year": 2018,
                "bio": "Author of the Earthsea series",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["full_name"] == "Ursula K. Le Guin"
        assert data["sort_name"] == "Le Guin, Ursula K."
        assert data["birth_year"] == 1929
        assert data["death_year"] == 2018
        assert data["bio"] == "Author of the Earthsea series"
        assert data["slug"] == "ursula-k-le-guin"

    async def test_missing_required_field_returns_422(self, admin_client: AsyncClient):
        response = await admin_client.post(
            "/api/v1/contributors/", json={"full_name": "No Sort Name"}
        )
        assert response.status_code == 422


class TestRetrieveContributorById:
    async def test_groups_books_and_releases_by_role(
        self,
        async_client: AsyncClient,
        contributor: ContributorModel,
        book: BookModel,
        release: ReleaseModel,
        book_contribution: BookContributor,
        release_contribution: ReleaseContributor,
    ):
        response = await async_client.get(f"/api/v1/contributors/{contributor.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(contributor.id)
        assert data["full_name"] == contributor.full_name
        assert data["sort_name"] == contributor.sort_name
        assert data["books_by_role"]["author"] == [
            {"id": str(book.id), "title": book.title}
        ]
        assert data["releases_by_role"]["narrator"] == [
            {
                "id": str(release.id),
                "format": release.format.value,
                "publisher": release.publisher,
                "language": release.language,
            }
        ]

    async def test_no_contributions_returns_empty_groupings(
        self, async_client: AsyncClient, contributor: ContributorModel
    ):
        response = await async_client.get(f"/api/v1/contributors/{contributor.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["books_by_role"] == {}
        assert data["releases_by_role"] == {}

    async def test_not_found(self, async_client: AsyncClient):
        response = await async_client.get(
            "/api/v1/contributors/00000000-0000-0000-0000-000000000000"
        )
        assert response.status_code == 404

    async def test_invalid_uuid(self, async_client: AsyncClient):
        response = await async_client.get("/api/v1/contributors/not-a-uuid")
        assert response.status_code == 422


class TestModifyContributor:
    async def test_requires_auth(
        self, async_client: AsyncClient, contributor: ContributorModel
    ):
        response = await async_client.patch(
            f"/api/v1/contributors/{contributor.id}", json={"full_name": "Renamed"}
        )
        assert response.status_code == 401

    async def test_forbidden_for_non_admin(
        self, reader_client: AsyncClient, contributor: ContributorModel
    ):
        response = await reader_client.patch(
            f"/api/v1/contributors/{contributor.id}", json={"full_name": "Renamed"}
        )
        assert response.status_code == 403

    async def test_not_found(self, admin_client: AsyncClient):
        response = await admin_client.patch(
            "/api/v1/contributors/00000000-0000-0000-0000-000000000000",
            json={"full_name": "Renamed"},
        )
        assert response.status_code == 404

    @pytest.mark.parametrize(
        ("field", "value"),
        [
            ("full_name", "Frank Patrick Herbert"),
            ("sort_name", "Herbert, Frank Patrick"),
            ("birth_year", 1920),
            ("death_year", 1986),
            ("bio", "American science fiction author"),
        ],
    )
    async def test_updates_each_field(
        self,
        admin_client: AsyncClient,
        contributor: ContributorModel,
        field: str,
        value: object,
    ):
        response = await admin_client.patch(
            f"/api/v1/contributors/{contributor.id}", json={field: value}
        )

        assert response.status_code == 200
        data = response.json()
        original = {
            "full_name": contributor.full_name,
            "sort_name": contributor.sort_name,
            "birth_year": contributor.birth_year,
            "death_year": contributor.death_year,
            "bio": contributor.bio,
        }
        for name, original_value in original.items():
            assert data[name] == (value if name == field else original_value)


class TestRetrieveContributorBooks:
    async def test_returns_paginated_books(
        self,
        async_client: AsyncClient,
        contributor: ContributorModel,
        book: BookModel,
        book_contribution: BookContributor,
    ):
        response = await async_client.get(
            f"/api/v1/contributors/{contributor.id}/books"
        )

        assert response.status_code == 200
        data = response.json()
        assert {"items", "total", "limit", "offset"} <= data.keys()
        assert [item["id"] for item in data["items"]] == [str(book.id)]

    async def test_no_books_returns_empty(
        self, async_client: AsyncClient, contributor: ContributorModel
    ):
        response = await async_client.get(
            f"/api/v1/contributors/{contributor.id}/books"
        )

        assert response.status_code == 200
        assert response.json()["items"] == []

    async def test_not_found(self, async_client: AsyncClient):
        response = await async_client.get(
            "/api/v1/contributors/00000000-0000-0000-0000-000000000000/books"
        )
        assert response.status_code == 404

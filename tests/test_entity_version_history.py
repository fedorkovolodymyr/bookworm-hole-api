from httpx import AsyncClient


class TestBookHistory:
    async def test_history_lists_version_after_create(self, admin_client: AsyncClient):
        create_response = await admin_client.post(
            "/api/v1/books/",
            json={"title": "Dune", "description": "Desert planet epic"},
        )
        assert create_response.status_code == 201
        book_id = create_response.json()["id"]

        history_response = await admin_client.get(f"/api/v1/books/{book_id}/history")
        assert history_response.status_code == 200
        data = history_response.json()
        assert data["total"] == 1
        assert data["items"][0]["entity_type"] == "book"
        assert data["items"][0]["entity_id"] == book_id
        assert data["items"][0]["version_number"] == 1
        assert data["items"][0]["change_source"] == "admin"

    async def test_history_rejects_limit_above_cap(self, admin_client: AsyncClient):
        create_response = await admin_client.post(
            "/api/v1/books/",
            json={"title": "Dune", "description": "Desert planet epic"},
        )
        book_id = create_response.json()["id"]

        response = await admin_client.get(
            f"/api/v1/books/{book_id}/history", params={"limit": 101}
        )
        assert response.status_code == 422

    async def test_history_records_new_version_on_update(
        self, admin_client: AsyncClient
    ):
        create_response = await admin_client.post(
            "/api/v1/books/",
            json={"title": "Dune", "description": "Desert planet epic"},
        )
        book_id = create_response.json()["id"]

        update_response = await admin_client.patch(
            f"/api/v1/books/{book_id}", json={"title": "Dune Messiah"}
        )
        assert update_response.status_code == 200

        history_response = await admin_client.get(f"/api/v1/books/{book_id}/history")
        data = history_response.json()
        assert data["total"] == 2
        versions = sorted(item["version_number"] for item in data["items"])
        assert versions == [1, 2]

    async def test_history_version_detail_returns_snapshot(
        self, admin_client: AsyncClient
    ):
        create_response = await admin_client.post(
            "/api/v1/books/",
            json={"title": "Dune", "description": "Desert planet epic"},
        )
        book_id = create_response.json()["id"]

        detail_response = await admin_client.get(f"/api/v1/books/{book_id}/history/1")
        assert detail_response.status_code == 200
        data = detail_response.json()
        assert data["version_number"] == 1
        assert data["snapshot"]["title"] == "Dune"

    async def test_history_version_not_found(self, admin_client: AsyncClient):
        create_response = await admin_client.post(
            "/api/v1/books/",
            json={"title": "Dune", "description": "Desert planet epic"},
        )
        book_id = create_response.json()["id"]

        response = await admin_client.get(f"/api/v1/books/{book_id}/history/99")
        assert response.status_code == 404


class TestReleaseHistory:
    async def test_history_lists_version_after_create(self, admin_client: AsyncClient):
        book_response = await admin_client.post(
            "/api/v1/books/",
            json={"title": "Dune", "description": "Desert planet epic"},
        )
        book_id = book_response.json()["id"]

        release_response = await admin_client.post(
            "/api/v1/releases/",
            json={
                "book_id": book_id,
                "format": "hardcover",
                "publisher": "Chilton Books",
                "language": "en",
            },
        )
        assert release_response.status_code == 201
        release_id = release_response.json()["id"]

        history_response = await admin_client.get(
            f"/api/v1/releases/{release_id}/history"
        )
        assert history_response.status_code == 200
        data = history_response.json()
        assert data["total"] == 1
        assert data["items"][0]["entity_type"] == "release"
        assert data["items"][0]["entity_id"] == release_id


class TestContributorHistory:
    async def test_history_lists_version_after_create(self, admin_client: AsyncClient):
        create_response = await admin_client.post(
            "/api/v1/contributors/",
            json={
                "full_name": "Frank Herbert",
                "sort_name": "Herbert, Frank",
                "slug": "frank-herbert",
            },
        )
        assert create_response.status_code == 201
        contributor_id = create_response.json()["id"]

        history_response = await admin_client.get(
            f"/api/v1/contributors/{contributor_id}/history"
        )
        assert history_response.status_code == 200
        data = history_response.json()
        assert data["total"] == 1
        assert data["items"][0]["entity_type"] == "contributor"
        assert data["items"][0]["entity_id"] == contributor_id

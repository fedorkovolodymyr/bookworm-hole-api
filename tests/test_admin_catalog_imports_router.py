import pytest
from arq import create_pool
from arq.connections import ArqRedis
from arq.connections import RedisSettings as ArqRedisSettings
from httpx import AsyncClient

from app.core.config import settings
from app.core.redis import get_redis_pool
from app.main import app

_TEST_REDIS_DB = 15


@pytest.fixture
async def redis_pool():
    redis_settings = settings.redis_settings
    pool = await create_pool(
        ArqRedisSettings(
            host=redis_settings.host,
            port=redis_settings.port,
            database=_TEST_REDIS_DB,
        )
    )
    await pool.flushdb()
    app.dependency_overrides[get_redis_pool] = lambda: pool
    yield pool
    await pool.flushdb()
    app.dependency_overrides.pop(get_redis_pool, None)
    await pool.aclose()


class TestTriggerCatalogImport:
    async def test_requires_authentication(self, async_client: AsyncClient):
        response = await async_client.post(
            "/api/v1/admin/catalog-imports", json={"profile": "books"}
        )
        assert response.status_code == 401

    async def test_requires_admin(
        self, reader_client: AsyncClient, redis_pool: ArqRedis
    ):
        response = await reader_client.post(
            "/api/v1/admin/catalog-imports", json={"profile": "books"}
        )
        assert response.status_code == 403

    async def test_enqueues_job(self, admin_client: AsyncClient, redis_pool: ArqRedis):
        response = await admin_client.post(
            "/api/v1/admin/catalog-imports", json={"profile": "comics"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["job_id"]
        assert data["status"] == "queued"
        assert data["result"] is None

    async def test_rejects_unknown_profile(
        self, admin_client: AsyncClient, redis_pool: ArqRedis
    ):
        response = await admin_client.post(
            "/api/v1/admin/catalog-imports", json={"profile": "cookbooks"}
        )
        assert response.status_code == 422


class TestGetCatalogImportStatus:
    async def test_returns_queued_status_for_pending_job(
        self, admin_client: AsyncClient, redis_pool: ArqRedis
    ):
        trigger = await admin_client.post(
            "/api/v1/admin/catalog-imports", json={"profile": "manga"}
        )
        job_id = trigger.json()["job_id"]

        response = await admin_client.get(f"/api/v1/admin/catalog-imports/{job_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["job_id"] == job_id
        assert data["status"] == "queued"
        assert data["result"] is None

    async def test_returns_404_for_unknown_job(
        self, admin_client: AsyncClient, redis_pool: ArqRedis
    ):
        response = await admin_client.get(
            "/api/v1/admin/catalog-imports/does-not-exist"
        )
        assert response.status_code == 404

    async def test_requires_admin(
        self, reader_client: AsyncClient, redis_pool: ArqRedis
    ):
        response = await reader_client.get("/api/v1/admin/catalog-imports/some-id")
        assert response.status_code == 403

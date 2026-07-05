from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.exc import SQLAlchemyError

from app.core.db import get_session
from app.main import app


@pytest.fixture
async def client():
    mock_session = AsyncMock()
    result = MagicMock()
    result.scalar.return_value = 1
    mock_session.execute.return_value = result

    async def override_get_session():
        yield mock_session

    app.dependency_overrides[get_session] = override_get_session
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac
    app.dependency_overrides.clear()


async def test_health_check_returns_200(client: AsyncClient):
    response = await client.get("/api/v1/health/")
    assert response.status_code == 200


async def test_health_check_response_shape(client: AsyncClient):
    response = await client.get("/api/v1/health/")
    data = response.json()
    assert "status" in data
    assert "checks" in data
    assert "api" in data["checks"]
    assert "database" in data["checks"]
    assert isinstance(data["version"], str)
    assert data["version"] != ""


async def test_health_live_returns_200():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/api/v1/health/live")
        assert response.status_code == 200


async def test_health_live_response():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/api/v1/health/live")
        data = response.json()
        assert data == {"status": "ok"}


async def test_health_ready_returns_200_when_db_ok(client: AsyncClient):
    response = await client.get("/api/v1/health/ready")
    assert response.status_code == 200


async def test_health_ready_response_when_db_ok(client: AsyncClient):
    response = await client.get("/api/v1/health/ready")
    data = response.json()
    assert data == {"status": "ok"}


async def test_health_ready_returns_503_when_db_fails():
    mock_session = AsyncMock()
    mock_session.execute.side_effect = SQLAlchemyError("Connection failed")

    async def override_get_session():
        yield mock_session

    app.dependency_overrides[get_session] = override_get_session
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/api/v1/health/ready")
        assert response.status_code == 503
    app.dependency_overrides.clear()


async def test_health_version_returns_200():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/api/v1/health/version")
        assert response.status_code == 200


async def test_health_version_has_version_field():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/api/v1/health/version")
        data = response.json()
        assert "version" in data
        assert isinstance(data["version"], str)

from datetime import datetime

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


class TestReadingStatsEndpoints:
    """High-level tests for reading stats endpoints."""

    @pytest.mark.asyncio
    async def test_stats_endpoint_no_auth_returns_401(self) -> None:
        """GET /me/reading/stats requires authentication."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/api/v1/me/reading/stats")
            assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_streak_endpoint_no_auth_returns_401(self) -> None:
        """GET /me/reading/streak requires authentication."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/api/v1/me/reading/streak")
            assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_timeline_endpoint_no_auth_returns_401(self) -> None:
        """GET /me/reading/timeline requires authentication."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            now = datetime.utcnow()
            response = await client.get(
                "/api/v1/me/reading/timeline",
                params={
                    "from_date": now.isoformat(),
                    "to_date": now.isoformat(),
                },
            )
            assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_stats_endpoint_query_params(self) -> None:
        """Test stats endpoint accepts valid period query params."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            for period in ["week", "month", "year", "all"]:
                response = await client.get(
                    "/api/v1/me/reading/stats", params={"period": period}
                )
                assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_timeline_endpoint_query_params(self) -> None:
        """Test timeline endpoint requires from_date and to_date."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            now = datetime.utcnow()
            response = await client.get(
                "/api/v1/me/reading/timeline",
                params={
                    "from_date": now.isoformat(),
                    "to_date": now.isoformat(),
                },
            )
            assert response.status_code == 401

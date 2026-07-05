import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from loguru import logger

from app.core.middleware import REQUEST_ID_HEADER
from app.main import app


@pytest.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac


@pytest.fixture
def captured_records():
    records: list[dict] = []
    sink_id = logger.add(lambda message: records.append(message.record), level="INFO")
    yield records
    logger.remove(sink_id)


class TestRequestLoggingMiddleware:
    async def test_generates_request_id_when_absent(self, client: AsyncClient):
        response = await client.get("/health")

        assert REQUEST_ID_HEADER in response.headers
        assert uuid.UUID(response.headers[REQUEST_ID_HEADER])

    async def test_reuses_incoming_request_id(self, client: AsyncClient):
        incoming_id = str(uuid.uuid4())

        response = await client.get("/health", headers={REQUEST_ID_HEADER: incoming_id})

        assert response.headers[REQUEST_ID_HEADER] == incoming_id

    async def test_logs_request_details(
        self, client: AsyncClient, captured_records: list[dict]
    ):
        response = await client.get("/health")

        record = next(
            r for r in captured_records if r["message"] == "request completed"
        )
        extra = record["extra"]
        assert extra["request_id"] == response.headers[REQUEST_ID_HEADER]
        assert extra["method"] == "GET"
        assert extra["path"] == "/health"
        assert extra["status"] == 200
        assert isinstance(extra["duration_ms"], float)

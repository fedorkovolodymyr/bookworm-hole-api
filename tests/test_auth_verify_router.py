from collections.abc import AsyncIterator

import pytest
from httpx import AsyncClient

from app.core.deps import get_email_verification_service
from app.core.errors import UnauthorizedError
from app.main import app
from app.models.user import User


class FakeEmailVerificationService:
    def __init__(self, confirmed_user: User | None = None, raises: bool = False):
        self.confirmed_user = confirmed_user
        self.raises = raises
        self.requested_for: list[User] = []
        self.confirmed_tokens: list[str] = []

    async def request_verification(self, user: User) -> None:
        self.requested_for.append(user)

    async def confirm_verification(self, token: str) -> User:
        self.confirmed_tokens.append(token)
        if self.raises or self.confirmed_user is None:
            raise UnauthorizedError("Invalid or expired verification token")
        return self.confirmed_user


@pytest.fixture
async def verification_service() -> AsyncIterator[FakeEmailVerificationService]:
    fake = FakeEmailVerificationService()
    app.dependency_overrides[get_email_verification_service] = lambda: fake
    yield fake
    app.dependency_overrides.pop(get_email_verification_service, None)


async def test_request_verification_calls_service_for_current_user(
    reader_client: AsyncClient,
    verification_service: FakeEmailVerificationService,
):
    response = await reader_client.post("/api/v1/auth/verify/request")

    assert response.status_code == 202
    assert len(verification_service.requested_for) == 1
    assert verification_service.requested_for[0].username == "reader"


async def test_request_verification_requires_authentication(
    async_client: AsyncClient,
    verification_service: FakeEmailVerificationService,
):
    response = await async_client.post("/api/v1/auth/verify/request")

    assert response.status_code in (401, 403)
    assert verification_service.requested_for == []


async def test_confirm_verification_marks_user_verified(
    async_client: AsyncClient,
    verification_service: FakeEmailVerificationService,
):
    verified_user = User(
        email="reader@example.com", username="reader", display_name="Reader"
    )
    verification_service.confirmed_user = verified_user

    response = await async_client.post(
        "/api/v1/auth/verify/confirm", json={"token": "valid-token"}
    )

    assert response.status_code == 200
    assert response.json()["email"] == "reader@example.com"
    assert verification_service.confirmed_tokens == ["valid-token"]


async def test_confirm_verification_rejects_invalid_token(
    async_client: AsyncClient,
    verification_service: FakeEmailVerificationService,
):
    verification_service.raises = True

    response = await async_client.post(
        "/api/v1/auth/verify/confirm", json={"token": "bad-token"}
    )

    assert response.status_code == 401

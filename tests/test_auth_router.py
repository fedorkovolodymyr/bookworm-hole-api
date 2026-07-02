import pytest
from fastapi import HTTPException, status
from httpx import ASGITransport, AsyncClient

from app.core.deps import get_auth_service, get_current_user
from app.main import app
from app.models.user import User
from app.schemas.auth_schemas import LoginSchema, RegisterSchema, TokenResponse


class FakeAuthService:
    def __init__(self):
        self.user = User(
            email="reader@example.com",
            username="reader",
            display_name="Reader",
        )
        self.tokens = TokenResponse(access_token="access", refresh_token="refresh")

    async def register(self, data: RegisterSchema):
        if data.email == "taken@example.com":
            raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered")
        return self.user, self.tokens

    async def login(self, data: LoginSchema):
        if data.password != "correct":
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid credentials")
        return self.user, self.tokens

    async def refresh(self, refresh_token: str):
        if refresh_token != "refresh":
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Refresh token revoked")
        return self.tokens

    async def logout(self, refresh_token: str) -> None:
        return None


@pytest.fixture
async def client():
    fake_service = FakeAuthService()
    app.dependency_overrides[get_auth_service] = lambda: fake_service
    app.dependency_overrides[get_current_user] = lambda: fake_service.user
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac
    app.dependency_overrides.clear()


async def test_register_success(client: AsyncClient):
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "reader@example.com",
            "username": "reader",
            "password": "s3cret!",
            "display_name": "Reader",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["user"]["email"] == "reader@example.com"
    assert data["access_token"] == "access"
    assert data["refresh_token"] == "refresh"


async def test_register_duplicate_email(client: AsyncClient):
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "taken@example.com",
            "username": "reader",
            "password": "s3cret!",
            "display_name": "Reader",
        },
    )
    assert response.status_code == 409


async def test_login_success(client: AsyncClient):
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "reader@example.com", "password": "correct"},
    )
    assert response.status_code == 200
    assert response.json()["access_token"] == "access"


async def test_login_wrong_password(client: AsyncClient):
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "reader@example.com", "password": "wrong"},
    )
    assert response.status_code == 401


async def test_refresh_success(client: AsyncClient):
    response = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": "refresh"}
    )
    assert response.status_code == 200
    assert response.json()["access_token"] == "access"


async def test_refresh_invalid_token(client: AsyncClient):
    response = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": "bogus"}
    )
    assert response.status_code == 401


async def test_logout_returns_no_content(client: AsyncClient):
    response = await client.post(
        "/api/v1/auth/logout", json={"refresh_token": "refresh"}
    )
    assert response.status_code == 204


async def test_me_returns_current_user(client: AsyncClient):
    response = await client.get(
        "/api/v1/auth/me", headers={"Authorization": "Bearer access"}
    )
    assert response.status_code == 200
    assert response.json()["email"] == "reader@example.com"


async def test_me_requires_bearer_token():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.get("/api/v1/auth/me")
    assert response.status_code in (401, 403)

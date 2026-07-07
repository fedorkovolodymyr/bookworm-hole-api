from urllib.parse import parse_qs, urlparse

import httpx
import pytest
import respx

from app.core.config import settings
from app.core.errors import ExternalServiceError
from app.services.external.google_oauth import GoogleOAuthAdapter

TOKEN_URL = "https://oauth2.googleapis.com/token"
REVOKE_URL = "https://oauth2.googleapis.com/revoke"


class TestBuildAuthorizationUrl:
    def test_includes_state_and_scope(self):
        adapter = GoogleOAuthAdapter()

        url = adapter.build_authorization_url("the-state")

        parsed = urlparse(url)
        query = parse_qs(parsed.query)
        assert parsed.netloc == "accounts.google.com"
        assert query["state"] == ["the-state"]
        assert query["access_type"] == ["offline"]
        assert query["prompt"] == ["consent"]
        assert query["scope"] == [" ".join(settings.google_oauth_settings.scopes)]
        assert query["redirect_uri"] == [settings.google_oauth_settings.redirect_uri]


class TestExchangeCode:
    @respx.mock
    async def test_returns_tokens_on_success(self):
        respx.post(TOKEN_URL).mock(
            return_value=httpx.Response(
                200,
                json={
                    "access_token": "access-token",
                    "refresh_token": "refresh-token",
                    "expires_in": 3600,
                    "scope": "https://www.googleapis.com/auth/drive.file",
                },
            )
        )
        adapter = GoogleOAuthAdapter()

        tokens = await adapter.exchange_code("auth-code")

        assert tokens.access_token == "access-token"
        assert tokens.refresh_token == "refresh-token"
        assert tokens.scopes == ["https://www.googleapis.com/auth/drive.file"]
        assert tokens.expires_at.tzinfo is not None

    @respx.mock
    async def test_raises_when_refresh_token_missing(self):
        respx.post(TOKEN_URL).mock(
            return_value=httpx.Response(
                200, json={"access_token": "access-token", "expires_in": 3600}
            )
        )
        adapter = GoogleOAuthAdapter()

        with pytest.raises(ExternalServiceError):
            await adapter.exchange_code("auth-code")

    @respx.mock
    async def test_raises_external_service_error_on_http_failure(self):
        respx.post(TOKEN_URL).mock(return_value=httpx.Response(400))
        adapter = GoogleOAuthAdapter()

        with pytest.raises(ExternalServiceError):
            await adapter.exchange_code("auth-code")


class TestRefresh:
    @respx.mock
    async def test_returns_refreshed_access_token(self):
        respx.post(TOKEN_URL).mock(
            return_value=httpx.Response(
                200, json={"access_token": "new-access-token", "expires_in": 1800}
            )
        )
        adapter = GoogleOAuthAdapter()

        tokens = await adapter.refresh("existing-refresh-token")

        assert tokens.access_token == "new-access-token"
        assert tokens.refresh_token == "existing-refresh-token"

    @respx.mock
    async def test_raises_external_service_error_on_http_failure(self):
        respx.post(TOKEN_URL).mock(return_value=httpx.Response(400))
        adapter = GoogleOAuthAdapter()

        with pytest.raises(ExternalServiceError):
            await adapter.refresh("existing-refresh-token")


class TestRevoke:
    @respx.mock
    async def test_succeeds(self):
        respx.post(REVOKE_URL).mock(return_value=httpx.Response(200))
        adapter = GoogleOAuthAdapter()

        await adapter.revoke("access-token")

    @respx.mock
    async def test_raises_external_service_error_on_http_failure(self):
        respx.post(REVOKE_URL).mock(return_value=httpx.Response(400))
        adapter = GoogleOAuthAdapter()

        with pytest.raises(ExternalServiceError):
            await adapter.revoke("access-token")

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import urlencode

import httpx

from app.core.config import settings
from app.core.errors import ErrorMessages, ExternalServiceError

_AUTH_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"
_TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
_REVOKE_ENDPOINT = "https://oauth2.googleapis.com/revoke"


@dataclass(frozen=True)
class GoogleOAuthTokens:
    access_token: str
    refresh_token: str
    expires_at: datetime
    scopes: list[str]


class GoogleOAuthAdapter:
    """Talks to Google's OAuth 2.0 endpoints directly over httpx for the Drive
    `drive.file` flow. All external calls are re-raised as ExternalServiceError."""

    def __init__(self) -> None:
        self._settings = settings.google_oauth_settings

    def build_authorization_url(self, state: str) -> str:
        params = {
            "client_id": self._settings.client_id,
            "redirect_uri": self._settings.redirect_uri,
            "response_type": "code",
            "scope": " ".join(self._settings.scopes),
            "access_type": "offline",
            "prompt": "consent",
            "include_granted_scopes": "true",
            "state": state,
        }
        return f"{_AUTH_ENDPOINT}?{urlencode(params)}"

    async def exchange_code(self, code: str) -> GoogleOAuthTokens:
        data = await self._post_token(
            ErrorMessages.GOOGLE_TOKEN_EXCHANGE_FAILED,
            grant_type="authorization_code",
            code=code,
            redirect_uri=self._settings.redirect_uri,
        )
        refresh_token: str | None = data.get("refresh_token")
        if not refresh_token:
            raise ExternalServiceError(ErrorMessages.GOOGLE_TOKEN_EXCHANGE_FAILED)
        return self._to_tokens(data, refresh_token=refresh_token)

    async def refresh(self, refresh_token: str) -> GoogleOAuthTokens:
        data = await self._post_token(
            ErrorMessages.GOOGLE_TOKEN_REFRESH_FAILED,
            grant_type="refresh_token",
            refresh_token=refresh_token,
        )
        return self._to_tokens(data, refresh_token=refresh_token)

    async def revoke(self, token: str) -> None:
        """Best-effort revocation against Google's endpoint. Raises
        ExternalServiceError on failure; callers decide whether to swallow it."""
        async with httpx.AsyncClient(timeout=5.0) as client:
            try:
                response = await client.post(_REVOKE_ENDPOINT, params={"token": token})
                response.raise_for_status()
            except httpx.HTTPError as exc:
                raise ExternalServiceError(
                    "Google token revocation request failed"
                ) from exc

    async def _post_token(self, error_message: str, **params: str) -> dict[str, Any]:
        payload = {
            "client_id": self._settings.client_id,
            "client_secret": self._settings.client_secret,
            **params,
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.post(_TOKEN_ENDPOINT, data=payload)
                response.raise_for_status()
            except httpx.HTTPError as exc:
                raise ExternalServiceError(error_message) from exc
            return response.json()

    def _to_tokens(self, data: dict[str, Any], refresh_token: str) -> GoogleOAuthTokens:
        access_token: str = data["access_token"]
        expires_in: int = int(data.get("expires_in", 3600))
        scope: str = data.get("scope") or " ".join(self._settings.scopes)
        return GoogleOAuthTokens(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_at=datetime.now(UTC) + timedelta(seconds=expires_in),
            scopes=scope.split(),
        )

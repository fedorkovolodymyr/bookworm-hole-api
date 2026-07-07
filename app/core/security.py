from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import jwt

from app.core.config import settings


def _encode_token(user_id: UUID, jti: str, expires_at: datetime) -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "iat": now,
        "exp": expires_at,
        "jti": jti,
    }
    return jwt.encode(
        payload,
        settings.auth_settings.secret_key,
        algorithm=settings.auth_settings.algorithm,
    )


def create_access_token(user_id: UUID) -> str:
    expires_at = datetime.now(UTC) + timedelta(
        minutes=settings.auth_settings.access_token_expire_minutes
    )
    return _encode_token(user_id, str(uuid4()), expires_at)


def create_refresh_token(user_id: UUID) -> tuple[str, str, datetime]:
    jti = str(uuid4())
    expires_at = datetime.now(UTC) + timedelta(
        days=settings.auth_settings.refresh_token_expire_days
    )
    token = _encode_token(user_id, jti, expires_at)
    return token, jti, expires_at


def decode_token(token: str) -> dict[str, str]:
    return jwt.decode(
        token,
        settings.auth_settings.secret_key,
        algorithms=[settings.auth_settings.algorithm],
    )


def create_oauth_state(user_id: UUID) -> str:
    """Signed, short-lived CSRF token binding an OAuth callback to the user who
    initiated it. Not stored server-side: JWT signature + expiry are the guarantee."""
    expires_at = datetime.now(UTC) + timedelta(
        minutes=settings.google_oauth_settings.state_expire_minutes
    )
    now = datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "purpose": "google_oauth_state",
        "iat": now,
        "exp": expires_at,
        "jti": str(uuid4()),
    }
    return jwt.encode(
        payload,
        settings.auth_settings.secret_key,
        algorithm=settings.auth_settings.algorithm,
    )


def decode_oauth_state(state: str) -> UUID:
    payload = jwt.decode(
        state,
        settings.auth_settings.secret_key,
        algorithms=[settings.auth_settings.algorithm],
    )
    if payload.get("purpose") != "google_oauth_state":
        raise jwt.InvalidTokenError("Unexpected token purpose")
    return UUID(payload["sub"])

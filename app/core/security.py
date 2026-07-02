from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import bcrypt
import jwt

from app.core.config import settings


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


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

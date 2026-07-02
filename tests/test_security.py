from datetime import UTC, datetime, timedelta
from uuid import uuid4

import jwt
import pytest

from app.core.config import settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)


def test_hash_password_round_trip():
    password_hash = hash_password("s3cret!")
    assert verify_password("s3cret!", password_hash)
    assert not verify_password("wrong", password_hash)


def test_create_access_token_has_expected_claims():
    user_id = uuid4()
    token = create_access_token(user_id)
    payload = decode_token(token)
    assert payload["sub"] == str(user_id)
    assert "exp" in payload
    assert "iat" in payload
    assert "jti" in payload
    delta = payload["exp"] - payload["iat"]
    assert delta == settings.auth_settings.access_token_expire_minutes * 60


def test_create_refresh_token_has_expected_expiry():
    user_id = uuid4()
    token, jti, expires_at = create_refresh_token(user_id)
    payload = decode_token(token)
    assert payload["jti"] == jti
    assert payload["sub"] == str(user_id)
    delta = payload["exp"] - payload["iat"]
    assert delta == settings.auth_settings.refresh_token_expire_days * 24 * 60 * 60
    assert expires_at > datetime.now(UTC)


def test_decode_token_rejects_expired_token():
    now = datetime.now(UTC)
    expired_payload = {
        "sub": str(uuid4()),
        "iat": now - timedelta(hours=1),
        "exp": now - timedelta(minutes=1),
        "jti": str(uuid4()),
    }
    token = jwt.encode(
        expired_payload,
        settings.auth_settings.secret_key,
        algorithm=settings.auth_settings.algorithm,
    )
    with pytest.raises(jwt.ExpiredSignatureError):
        decode_token(token)


def test_decode_token_rejects_tampered_signature():
    token = create_access_token(uuid4())
    tampered = token[:-1] + ("a" if token[-1] != "a" else "b")
    with pytest.raises(jwt.InvalidSignatureError):
        decode_token(tampered)

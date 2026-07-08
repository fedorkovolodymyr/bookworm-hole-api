import pytest
from fastapi import HTTPException

from app.core.deps import get_current_user_optional, require_admin
from app.models.user import User


class FakeAuthService:
    def __init__(self, user: User | None = None, raises: bool = False):
        self.user = user
        self.raises = raises

    async def get_current_user(self, access_token: str) -> User:
        if self.raises:
            raise HTTPException(401, "Invalid access token")
        assert self.user is not None
        return self.user


async def test_get_current_user_optional_no_credentials():
    result = await get_current_user_optional(
        credentials=None, auth_service=FakeAuthService()
    )
    assert result is None


async def test_get_current_user_optional_valid_token():
    user = User(email="reader@example.com", username="reader", display_name="Reader")
    credentials = type("Credentials", (), {"credentials": "valid-token"})()
    result = await get_current_user_optional(
        credentials=credentials, auth_service=FakeAuthService(user=user)
    )
    assert result is user


async def test_get_current_user_optional_invalid_token():
    credentials = type("Credentials", (), {"credentials": "bad-token"})()
    with pytest.raises(HTTPException) as exc_info:
        await get_current_user_optional(
            credentials=credentials, auth_service=FakeAuthService(raises=True)
        )
    assert exc_info.value.status_code == 401


async def test_require_admin_passes_for_admin():
    admin = User(
        email="admin@example.com",
        username="admin",
        display_name="Admin",
        is_admin=True,
    )
    result = await anext(require_admin(current_user=admin))
    assert result is admin


async def test_require_admin_raises_for_non_admin():
    user = User(email="reader@example.com", username="reader", display_name="Reader")
    with pytest.raises(HTTPException) as exc_info:
        await anext(require_admin(current_user=user))
    assert exc_info.value.status_code == 403

import pytest
from sqlalchemy import inspect

from app.models.user import User


def test_user_table_columns():
    columns = inspect(User).columns
    expected = {
        "id",
        "email",
        "username",
        "password_hash",
        "display_name",
        "avatar_url",
        "bio",
        "locale",
        "timezone",
        "is_active",
        "is_admin",
        "created_at",
        "updated_at",
    }
    assert expected.issubset(columns.keys())
    assert columns["email"].unique
    assert columns["username"].unique
    assert columns["password_hash"].nullable


def test_user_defaults():
    user = User(email="reader@example.com", username="reader", display_name="Reader")
    assert user.password_hash is None
    assert user.locale == "en"
    assert user.timezone == "UTC"
    assert user.is_active is True
    assert user.is_admin is False


def test_user_locale_rejects_invalid_value():
    with pytest.raises(ValueError):
        User.model_validate(
            {
                "email": "reader@example.com",
                "username": "reader",
                "display_name": "Reader",
                "locale": "not-a-locale",
            }
        )


def test_user_locale_accepts_bcp47_tag():
    user = User.model_validate(
        {
            "email": "reader@example.com",
            "username": "reader",
            "display_name": "Reader",
            "locale": "pt-BR",
        }
    )
    assert user.locale == "pt-BR"

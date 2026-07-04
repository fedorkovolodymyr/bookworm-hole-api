import pytest

from app.core.config import AuthSettings, Settings, get_settings


def test_get_settings_is_cached():
    assert get_settings() is get_settings()


def test_app_env_defaults_to_dev():
    assert get_settings().app_settings.app_env == "dev"


def test_database_url_falls_back_to_postgres_dsn():
    settings = get_settings()
    assert settings.database_url == settings.postgres_settings.DB_URI


def test_database_url_honors_override(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://override/db")
    assert get_settings().database_url == "postgresql+asyncpg://override/db"


def test_cors_origins_parses_comma_separated_env(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("CORS_ORIGINS", "http://a.com, http://b.com")
    assert get_settings().app_settings.cors_origins == ["http://a.com", "http://b.com"]


def test_prod_env_with_default_secret_key_raises(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("APP_ENV", "prod")
    with pytest.raises(RuntimeError):
        Settings()


def test_prod_env_with_custom_secret_key_succeeds(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("APP_ENV", "prod")
    monkeypatch.setenv("AUTH_SECRET_KEY", "a-real-random-secret")
    settings = Settings()
    assert settings.app_settings.app_env == "prod"
    assert (
        settings.auth_settings.secret_key
        != AuthSettings.model_fields["secret_key"].default
    )


def test_sentry_settings_defaults_to_disabled():
    assert get_settings().sentry_settings.dsn is None


def test_sentry_settings_reads_env(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("SENTRY_DSN", "https://example@sentry.io/1")
    monkeypatch.setenv("SENTRY_TRACES_SAMPLE_RATE", "0.5")
    monkeypatch.setenv("SENTRY_PROFILES_SAMPLE_RATE", "0.2")
    sentry_settings = get_settings().sentry_settings
    assert sentry_settings.dsn == "https://example@sentry.io/1"
    assert sentry_settings.traces_sample_rate == 0.5
    assert sentry_settings.profiles_sample_rate == 0.2

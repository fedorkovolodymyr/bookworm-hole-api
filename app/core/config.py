from functools import lru_cache
from typing import Annotated, Literal
from urllib.parse import quote

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class APISettings(BaseSettings):
    api_v1_str: str = "/api/v1"
    api_port: int = 8000

    model_config = SettingsConfigDict(
        case_sensitive=False,
        extra="ignore",
        env_file=".env",
        env_file_encoding="utf-8",
    )


class PostgresSettings(BaseSettings):
    user: str = "bookwormhole"
    password: str = "bookwormhole"
    db: str = "bookwormhole"
    port: int = 5432
    host: str = "localhost"
    echo_sql: bool = False
    pool_size: int = 5
    max_overflow: int = 10

    @property
    def DB_URI(self) -> str:
        return (
            f"postgresql+asyncpg://{quote(self.user, safe='')}:"
            f"{quote(self.password, safe='')}@{self.host}:"
            f"{self.port}/{self.db}"
        )

    model_config = SettingsConfigDict(
        env_prefix="POSTGRES_",
        case_sensitive=False,
        extra="ignore",
        env_file=".env",
        env_file_encoding="utf-8",
    )


class RedisSettings(BaseSettings):
    host: str = "localhost"
    port: int = 6379
    db: int = 0

    model_config = SettingsConfigDict(
        env_prefix="REDIS_",
        case_sensitive=False,
        extra="ignore",
        env_file=".env",
        env_file_encoding="utf-8",
    )


class AuthSettings(BaseSettings):
    secret_key: str = "dev-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 30
    password_reset_token_expire_minutes: int = 1440

    model_config = SettingsConfigDict(
        env_prefix="AUTH_",
        case_sensitive=False,
        extra="ignore",
        env_file=".env",
        env_file_encoding="utf-8",
    )


class AppSettings(BaseSettings):
    app_env: Literal["dev", "test", "prod"] = "dev"
    log_level: str = "INFO"
    cors_origins: Annotated[list[str], NoDecode] = []
    database_url: str | None = None
    # Replace-mode Google Drive restore hard-wipes the account before writing
    # the backup back — kept opt-in for MVP until a re-auth flow exists.
    enable_backup_replace_mode: bool = False

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_cors_origins(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    model_config = SettingsConfigDict(
        case_sensitive=False,
        extra="ignore",
        env_file=".env",
        env_file_encoding="utf-8",
    )


class OpenLibrarySettings(BaseSettings):
    base_url: str = "https://openlibrary.org"
    covers_base_url: str = "https://covers.openlibrary.org"
    timeout_seconds: float = 5.0
    retries: int = 2

    model_config = SettingsConfigDict(
        env_prefix="OPEN_LIBRARY_",
        case_sensitive=False,
        extra="ignore",
        env_file=".env",
        env_file_encoding="utf-8",
    )


class GoogleBooksSettings(BaseSettings):
    base_url: str = "https://www.googleapis.com/books/v1"
    api_key: str | None = None
    timeout_seconds: float = 5.0
    retries: int = 2

    model_config = SettingsConfigDict(
        env_prefix="GOOGLE_BOOKS_",
        case_sensitive=False,
        extra="ignore",
        env_file=".env",
        env_file_encoding="utf-8",
    )


class MailerSettings(BaseSettings):
    backend: Literal["console", "smtp"] = "console"
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_from_email: str = "noreply@bookwormhole.app"

    model_config = SettingsConfigDict(
        env_prefix="MAILER_",
        case_sensitive=False,
        extra="ignore",
        env_file=".env",
        env_file_encoding="utf-8",
    )


class EncryptionSettings(BaseSettings):
    # Valid Fernet key so the dev/test default works out of the box; never used in prod
    # (see Settings.__init__ check below).
    key: str = "IXfPzT7cW1RQq9wV5Hn2mA8sK0eB3dL6oJ4uY_gN7pk="

    model_config = SettingsConfigDict(
        env_prefix="ENCRYPTION_",
        case_sensitive=False,
        extra="ignore",
        env_file=".env",
        env_file_encoding="utf-8",
    )


class GoogleOAuthSettings(BaseSettings):
    client_id: str = ""
    client_secret: str = ""
    redirect_uri: str = "http://localhost:8000/api/v1/integrations/google/callback"
    scopes: Annotated[list[str], NoDecode] = [
        "https://www.googleapis.com/auth/drive.file"
    ]
    state_expire_minutes: int = 10

    @field_validator("scopes", mode="before")
    @classmethod
    def _split_scopes(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, str):
            return [scope.strip() for scope in value.split(",") if scope.strip()]
        return value

    model_config = SettingsConfigDict(
        env_prefix="GOOGLE_OAUTH_",
        case_sensitive=False,
        extra="ignore",
        env_file=".env",
        env_file_encoding="utf-8",
    )


class SentrySettings(BaseSettings):
    dsn: str | None = None
    traces_sample_rate: float = 0.0
    profiles_sample_rate: float = 0.0

    model_config = SettingsConfigDict(
        env_prefix="SENTRY_",
        case_sensitive=False,
        extra="ignore",
        env_file=".env",
        env_file_encoding="utf-8",
    )


class AISettings(BaseSettings):
    provider: str = "noop"

    model_config = SettingsConfigDict(
        env_prefix="AI_",
        case_sensitive=False,
        extra="ignore",
        env_file=".env",
        env_file_encoding="utf-8",
    )


class Settings:
    def __init__(self):
        self.api_settings = APISettings()
        self.postgres_settings = PostgresSettings()
        self.redis_settings = RedisSettings()
        self.auth_settings = AuthSettings()
        self.app_settings = AppSettings()
        self.open_library_settings = OpenLibrarySettings()
        self.google_books_settings = GoogleBooksSettings()
        self.google_oauth_settings = GoogleOAuthSettings()
        self.encryption_settings = EncryptionSettings()
        self.sentry_settings = SentrySettings()
        self.mailer_settings = MailerSettings()
        self.ai_settings = AISettings()

        if (
            self.app_settings.app_env == "prod"
            and self.auth_settings.secret_key
            == AuthSettings.model_fields["secret_key"].default
        ):
            raise RuntimeError(
                "AUTH_SECRET_KEY must be set to a non-default value when APP_ENV=prod"
            )

        if (
            self.mailer_settings.backend == "smtp"
            and not self.mailer_settings.smtp_host
        ):
            raise RuntimeError("MAILER_SMTP_HOST must be set when MAILER_BACKEND=smtp")

        if (
            self.app_settings.app_env == "prod"
            and self.encryption_settings.key
            == EncryptionSettings.model_fields["key"].default
        ):
            raise RuntimeError(
                "ENCRYPTION_KEY must be set to a non-default value when APP_ENV=prod"
            )

    @property
    def database_url(self) -> str:
        return self.app_settings.database_url or self.postgres_settings.DB_URI

    @property
    def google_books_api_key(self) -> str | None:
        return self.google_books_settings.api_key


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

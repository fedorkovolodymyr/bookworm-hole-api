from urllib.parse import quote

from pydantic_settings import BaseSettings, SettingsConfigDict


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


class Settings:
    def __init__(self):
        self.api_settings = APISettings()
        self.postgres_settings = PostgresSettings()


settings = Settings()

from pydantic_settings import BaseSettings, SettingsConfigDict


class APISettings(BaseSettings):
    API_V1_STR: str = "/api/v1"
    API_PORT: int = 8000

    model_config = SettingsConfigDict()


class PostgresSettings(BaseSettings):
    user: str = "bookwormhole"
    password: str = "bookwormhole"
    db: str = "bookwormhole"
    port: int = 5432
    host: str = "postgres"
    echo_sql: bool = False

    @property
    def DB_URI(self) -> str:
        return (
            f"postgresql+asyncpg://{self.user}:"
            f"{self.password}@{self.host}:"
            f"{self.port}/{self.db}"
        )

    model_config = SettingsConfigDict(env_prefix="POSTGRES_")


class Settings(BaseSettings):
    api_settings: APISettings = APISettings()
    postgres_settings: PostgresSettings = PostgresSettings()

    model_config = SettingsConfigDict()


settings = Settings()

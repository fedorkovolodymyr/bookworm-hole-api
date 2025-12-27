from pydantic_settings import BaseSettings, SettingsConfigDict


class APISerrings(BaseSettings):
    API_V1_STR = "/api/v1"
    API_PORT = 8000

    model_config = SettingsConfigDict()


class PostgresSettings(BaseSettings):
    USER: str = "bookwormhole"
    PASSWORD: str = "bookwormhole"
    DB: str = "bookwormhole"
    PORT: int = 5432
    ECHO_SQL: bool = False

    @property
    def DB_URI(self) -> str:
        return (
            f"postgresql+asyncpg://{self.USER}:"
            f"{self.PASSWORD}@localhost:"
            f"{self.PORT}/{self.DB}"
        )

    model_config = SettingsConfigDict(env_prefix="POSTGRES_")


class Settings(BaseSettings):
    api_settings: APISerrings = APISerrings()
    postgres_settings: PostgresSettings = PostgresSettings()

    model_config = SettingsConfigDict()


settings = Settings()

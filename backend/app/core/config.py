"""Environment-based application settings."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration loaded from environment variables or .env."""

    app_name: str = "SecGraph API"
    environment: str = "development"
    database_url: str = (
        "postgresql+psycopg://secgraph:secgraph@localhost:5432/secgraph"
    )
    log_level: str = "INFO"
    storage_dir: str = "storage/projects"
    max_upload_size_bytes: int = 50 * 1024 * 1024

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """Return the cached application settings."""

    return Settings()

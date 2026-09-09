"""Environment-based application settings."""

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration loaded from environment variables or .env."""

    app_name: str = "SecGraph API"
    environment: str = "development"
    database_url: str = (
        "postgresql+psycopg://secgraph:secgraph@localhost:5432/secgraph"
    )
    log_level: str = "INFO"
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"
    storage_dir: str = "storage/projects"
    max_upload_size_bytes: int = 50 * 1024 * 1024
    max_archive_uncompressed_bytes: int = 250 * 1024 * 1024
    max_archive_member_bytes: int = 25 * 1024 * 1024
    max_archive_members: int = 10_000
    api_auth_enabled: bool = True
    api_keys: str = ""
    rate_limit_enabled: bool = True
    rate_limit_requests: int = 120
    rate_limit_window_seconds: int = 60
    github_token: str | None = None
    github_webhook_secret: str | None = None
    github_api_url: str = "https://api.github.com"
    github_timeout_seconds: float = 30.0
    redis_url: str = "redis://localhost:6379/0"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "deepseek-r1:1.5b"
    ollama_complex_model: str = "deepseek-r1:7b"
    groq_api_key: str | None = None
    groq_model: str = "deepseek-r1:7b"
    ai_timeout_seconds: float = 30.0
    ai_provider: Literal["auto", "ollama", "groq"] = "auto"
    ai_routing_enabled: bool = True
    ai_skip_high_confidence: bool = True
    ai_static_confidence_threshold: float = 0.85
    ai_simple_confidence_threshold: float = 0.75
    ai_complex_rule_ids: str = "possible-idor,sensitive-data-exposure"
    ai_prefer_groq_for_complex: bool = True

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

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
    redis_url: str = "redis://localhost:6379/0"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "deepseek-r1:1.5b"
    ollama_complex_model: str = "deepseek-r1:7b"
    groq_api_key: str | None = None
    groq_model: str = "deepseek-r1:7b"
    ai_timeout_seconds: float = 30.0
    ai_routing_enabled: bool = True
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

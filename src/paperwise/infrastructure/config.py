from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env.local", ".env"),
        env_prefix="PAPERWISE_",
        extra="ignore",
    )

    env: str = "local"
    log_level: str = "INFO"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    redis_url: str = "redis://localhost:6379/0"
    repository_backend: str = "memory"
    postgres_url: str = "postgresql+psycopg://paperwise:paperwise@localhost:5432/paperwise"
    object_store_root: str = "local/object-store"
    openai_api_key: str | None = None
    openai_model: str = "gpt-4.1-mini"
    openai_base_url: str = "https://api.openai.com/v1"
    auth_secret: str = "paperwise-dev-secret-change-me"
    auth_token_ttl_seconds: int = 60 * 60 * 12


@lru_cache
def get_settings() -> Settings:
    return Settings()

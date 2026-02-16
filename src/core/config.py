from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "Market Sentinel"
    debug: bool = False
    log_level: str = "INFO"

    # Database
    database_url: str = "postgresql+asyncpg://sentinel:sentinel@postgres:5432/sentinel"

    # Redis
    redis_url: str = "redis://redis:6379/0"

    # Scraper
    scraper_concurrency: int = 50
    scraper_timeout: int = 30
    scraper_max_retries: int = 3
    scraper_retry_min_wait: float = 1.0
    scraper_retry_max_wait: float = 10.0


@lru_cache
def get_settings() -> Settings:
    return Settings()

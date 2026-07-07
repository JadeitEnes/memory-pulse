from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    APP_NAME: str = "Memory Pulse"
    APP_VERSION: str = "0.1.0"
    ENVIRONMENT: Literal["development", "staging", "production"] = "development"
    DEBUG: bool = False

    API_V1_PREFIX: str = "/api/v1"
    ALLOWED_ORIGINS: list[str] = Field(default=["http://localhost:3000", "http://localhost:5173"])

    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://memory_user:memory_pass@localhost:5432/memory_pulse"
    )

    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_TIMEOUT: int = 30

    REDIS_BROKER_URL: str = "redis://localhost:6379/0"
    REDIS_CACHE_URL: str = "redis://localhost:6380/0"

    CACHE_TTL_PRICES: int = 300
    CACHE_TTL_MARKET_SUMMARY: int = 600
    CACHE_TTL_SUMMARY: int = 600

    SECRET_KEY: str = Field(default="change-me-in-production-use-secrets-module")
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24
    API_USERNAME: str = "admin"
    API_PASSWORD: str = "changeme"

    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    LOG_FORMAT: Literal["json", "console"] = "console"

    SCRAPER_REQUEST_DELAY_SECONDS: float = 2.0
    SCRAPER_MAX_RETRIES: int = 3
    SCRAPER_TIMEOUT_SECONDS: int = 30
    USER_AGENT: str = "Mozilla/5.0 (compatible; MemoryPulseBot/1.0; +https://example.com/bot)"

    PRICE_COLLECTION_INTERVAL_MINUTES: int = 360
    WS_BROADCAST_INTERVAL_SECONDS: float = 5.0

    @field_validator("ENVIRONMENT")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        return v

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"

    @property
    def is_development(self) -> bool:
        return self.ENVIRONMENT == "development"


@lru_cache(maxsize=1)
def get_settings() -> Settings:

    return Settings()

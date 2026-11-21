from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables and the root `.env` file."""

    model_config = SettingsConfigDict(env_file=("../.env", ".env"), extra="ignore")

    app_name: str = "BrewPass API"
    environment: Literal["development", "test", "production"] = "development"
    database_url: str = "postgresql+psycopg://brewpass:brewpass@localhost:5432/brewpass"
    cors_origins: list[str] = ["http://localhost:5173"]

    log_level: str = "INFO"
    log_format: Literal["json", "text"] = "json"

    rate_limit_enabled: bool = True
    # Default limit per client IP for every endpoint (limits syntax, e.g. "120/minute").
    rate_limit_default: str = "120/minute"

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()

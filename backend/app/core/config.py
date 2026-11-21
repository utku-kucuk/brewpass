from functools import lru_cache
from typing import Literal

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEV_JWT_SECRET = "dev-only-insecure-secret-change-me-0123456789"


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

    # Auth
    jwt_secret_key: str = DEV_JWT_SECRET
    jwt_algorithm: str = "HS256"
    access_token_ttl_minutes: int = 15
    refresh_token_ttl_days: int = 30
    otp_ttl_minutes: int = 5
    otp_max_attempts: int = 5
    # Fixed OTP used outside production, where no SMS provider is wired up.
    otp_mock_code: str = "1234"

    @model_validator(mode="after")
    def _require_real_secret_in_production(self) -> "Settings":
        if self.is_production and self.jwt_secret_key == DEV_JWT_SECRET:
            raise ValueError("JWT_SECRET_KEY must be set in production.")
        return self

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()

from pathlib import Path
from typing import Literal

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEV_INTERNAL_TOKEN = "dev-internal-token-change-me"


class ServiceSettings(BaseSettings):
    """Settings every service shares. Services subclass this and add their own fields."""

    model_config = SettingsConfigDict(env_file=(".env",), extra="ignore")

    service_name: str = "brewpass"
    environment: Literal["development", "test", "production"] = "development"
    database_url: str = "postgresql+psycopg://brewpass:brewpass@localhost:5432/brewpass"
    cors_origins: list[str] = ["http://localhost:5173"]

    log_level: str = "INFO"
    log_format: Literal["json", "text"] = "json"

    rate_limit_enabled: bool = True
    rate_limit_default: str = "120/minute"

    # Access tokens are signed by the auth service (RS256) and verified locally everywhere.
    jwt_algorithm: str = "RS256"
    jwt_issuer: str = "brewpass-auth"
    jwt_public_key: str | None = None
    jwt_public_key_file: Path | None = None

    # Shared secret for service-to-service calls on /internal routes.
    internal_token: str = DEV_INTERNAL_TOKEN

    @model_validator(mode="after")
    def _load_public_key(self) -> "ServiceSettings":
        if self.jwt_public_key is None and self.jwt_public_key_file is not None:
            self.jwt_public_key = self.jwt_public_key_file.read_text()
        if self.is_production and self.internal_token == DEV_INTERNAL_TOKEN:
            raise ValueError("INTERNAL_TOKEN must be set in production.")
        return self

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

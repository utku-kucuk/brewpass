from functools import lru_cache
from pathlib import Path

from pydantic import model_validator

from brewpass_common.config import ServiceSettings


class AuthSettings(ServiceSettings):
    service_name: str = "auth"
    database_url: str = "postgresql+psycopg://brewpass:brewpass@localhost:5432/brewpass_auth"

    # RS256 private key: only the auth service can issue access tokens.
    jwt_private_key: str | None = None
    jwt_private_key_file: Path | None = None

    access_token_ttl_minutes: int = 15
    refresh_token_ttl_days: int = 30
    otp_ttl_minutes: int = 5
    otp_max_attempts: int = 5
    # Fixed OTP used outside production, where no SMS provider is wired up.
    otp_mock_code: str = "1234"
    # Server-side secret used to hash OTP codes and refresh tokens at rest.
    hash_secret: str = "dev-only-hash-secret-change-me"

    @model_validator(mode="after")
    def _load_private_key(self) -> "AuthSettings":
        if self.jwt_private_key is None and self.jwt_private_key_file is not None:
            self.jwt_private_key = self.jwt_private_key_file.read_text()
        if not self.jwt_private_key or not self.jwt_public_key:
            raise ValueError(
                "JWT key pair is missing. Run scripts/generate-dev-keys.sh or set "
                "JWT_PRIVATE_KEY(_FILE) and JWT_PUBLIC_KEY(_FILE)."
            )
        if self.is_production and self.hash_secret.startswith("dev-only"):
            raise ValueError("HASH_SECRET must be set in production.")
        return self


@lru_cache
def get_settings() -> AuthSettings:
    return AuthSettings()

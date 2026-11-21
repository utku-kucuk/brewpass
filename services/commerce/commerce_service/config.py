from functools import lru_cache

from pydantic import model_validator

from brewpass_common.config import ServiceSettings


class CommerceSettings(ServiceSettings):
    service_name: str = "commerce"
    database_url: str = "postgresql+psycopg://brewpass:brewpass@localhost:5432/brewpass_commerce"

    # Other services this one calls on their /internal routes.
    catalog_service_url: str = "http://localhost:8002"
    payment_service_url: str = "http://localhost:8004"

    # Secret for HMAC-SHA256 signatures on pickup QR codes.
    qr_signing_secret: str = "dev-only-qr-secret-change-me"
    # Refuse orders while the shop is closed (turn off only for demos at night).
    enforce_opening_hours: bool = True

    @model_validator(mode="after")
    def _require_real_qr_secret(self) -> "CommerceSettings":
        if self.is_production and self.qr_signing_secret.startswith("dev-only"):
            raise ValueError("QR_SIGNING_SECRET must be set in production.")
        return self


@lru_cache
def get_settings() -> CommerceSettings:
    return CommerceSettings()

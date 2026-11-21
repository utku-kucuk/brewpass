from functools import lru_cache

from brewpass_common.config import ServiceSettings


class CommerceSettings(ServiceSettings):
    service_name: str = "commerce"
    database_url: str = "postgresql+psycopg://brewpass:brewpass@localhost:5432/brewpass_commerce"

    # Other services this one calls on their /internal routes.
    catalog_service_url: str = "http://localhost:8002"
    payment_service_url: str = "http://localhost:8004"


@lru_cache
def get_settings() -> CommerceSettings:
    return CommerceSettings()

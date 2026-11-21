from functools import lru_cache

from brewpass_common.config import ServiceSettings


class CatalogSettings(ServiceSettings):
    service_name: str = "catalog"
    database_url: str = "postgresql+psycopg://brewpass:brewpass@localhost:5432/brewpass_catalog"
    # Opening hours are stored as local wall-clock times in this zone.
    shop_timezone: str = "Europe/Istanbul"


@lru_cache
def get_settings() -> CatalogSettings:
    return CatalogSettings()

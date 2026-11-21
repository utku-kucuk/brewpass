from functools import lru_cache

from brewpass_common.config import ServiceSettings


class PaymentSettings(ServiceSettings):
    service_name: str = "payment"
    database_url: str = "postgresql+psycopg://brewpass:brewpass@localhost:5432/brewpass_payment"


@lru_cache
def get_settings() -> PaymentSettings:
    return PaymentSettings()

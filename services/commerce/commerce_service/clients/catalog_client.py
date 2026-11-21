"""Reads products and shops from the catalog service's internal API."""

import uuid
from dataclasses import dataclass
from functools import lru_cache

from brewpass_common.internal_client import InternalClient
from commerce_service.config import get_settings


@dataclass(frozen=True)
class ShopInfo:
    id: uuid.UUID
    name: str
    owner_id: uuid.UUID | None
    is_active: bool
    is_open_now: bool


@dataclass(frozen=True)
class ProductInfo:
    id: uuid.UUID
    name: str
    supports_milk: bool
    supports_extra_shot: bool
    is_available: bool
    shop: ShopInfo


class CatalogClient:
    def __init__(self, client: InternalClient) -> None:
        self._client = client

    def get_product(self, product_id: uuid.UUID) -> ProductInfo:
        """Raises the catalog's `404 PRODUCT_NOT_FOUND`, or `503` if it cannot be reached."""
        data = self._client.get(f"/internal/products/{product_id}")
        shop = data["shop"]
        return ProductInfo(
            id=uuid.UUID(data["id"]),
            name=data["name"],
            supports_milk=data["supports_milk"],
            supports_extra_shot=data["supports_extra_shot"],
            is_available=data["is_available"],
            shop=ShopInfo(
                id=uuid.UUID(shop["id"]),
                name=shop["name"],
                owner_id=uuid.UUID(shop["owner_id"]) if shop["owner_id"] else None,
                is_active=shop["is_active"],
                is_open_now=shop["is_open_now"],
            ),
        )


@lru_cache
def get_catalog_client() -> CatalogClient:
    settings = get_settings()
    return CatalogClient(InternalClient(settings.catalog_service_url, settings.internal_token))

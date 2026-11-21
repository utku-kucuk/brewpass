"""Importing this package registers every catalog table on `Base.metadata`."""

from catalog_service.models.product import Product, ProductCategory
from catalog_service.models.shop import Shop, ShopOpeningHours

__all__ = ["Product", "ProductCategory", "Shop", "ShopOpeningHours"]

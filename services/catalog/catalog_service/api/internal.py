"""Routes other services call (never exposed by the gateway)."""

import uuid
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from brewpass_common.errors import NotFoundError
from brewpass_common.responses import ApiResponse, ok
from brewpass_common.security import require_internal_token
from catalog_service.db import get_db
from catalog_service.models import Product, ProductCategory, Shop

router = APIRouter(
    prefix="/internal", tags=["internal"], dependencies=[Depends(require_internal_token)]
)
DbSession = Annotated[Session, Depends(get_db)]


class InternalShopOut(BaseModel):
    id: uuid.UUID
    name: str
    owner_id: uuid.UUID | None
    is_active: bool


class InternalProductOut(BaseModel):
    id: uuid.UUID
    name: str
    category: ProductCategory
    list_price: Decimal
    supports_milk: bool
    supports_extra_shot: bool
    is_available: bool
    shop: InternalShopOut


def _shop_out(shop: Shop) -> InternalShopOut:
    return InternalShopOut(
        id=shop.id, name=shop.name, owner_id=shop.owner_id, is_active=shop.is_active
    )


@router.get("/shops/{shop_id}", response_model=ApiResponse[InternalShopOut])
def get_shop(shop_id: uuid.UUID, db: DbSession) -> ApiResponse[InternalShopOut]:
    shop = db.get(Shop, shop_id)
    if shop is None:
        raise NotFoundError("Shop not found.", code="SHOP_NOT_FOUND")
    return ok(_shop_out(shop))


@router.get("/products/{product_id}", response_model=ApiResponse[InternalProductOut])
def get_product(product_id: uuid.UUID, db: DbSession) -> ApiResponse[InternalProductOut]:
    product = db.get(Product, product_id)
    if product is None:
        raise NotFoundError("Drink not found.", code="PRODUCT_NOT_FOUND")
    return ok(
        InternalProductOut(
            id=product.id,
            name=product.name,
            category=product.category,
            list_price=product.list_price,
            supports_milk=product.supports_milk,
            supports_extra_shot=product.supports_extra_shot,
            is_available=product.is_available,
            shop=_shop_out(product.shop),
        )
    )

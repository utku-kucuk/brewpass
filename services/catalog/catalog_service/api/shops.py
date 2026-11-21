import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from brewpass_common.errors import UnprocessableError
from brewpass_common.responses import ApiResponse, ok
from catalog_service.db import get_db
from catalog_service.schemas.shop import MenuOut, ShopDetailOut, ShopPage, ShopSearchQuery
from catalog_service.services.shop_service import ShopService

router = APIRouter(prefix="/api/v1/shops", tags=["shops"])


def get_now() -> datetime:
    """Current time; overridden in tests to check opening hours deterministically."""
    return datetime.now(UTC)


def get_shop_service(
    db: Annotated[Session, Depends(get_db)], now: Annotated[datetime, Depends(get_now)]
) -> ShopService:
    return ShopService(db, now)


Service = Annotated[ShopService, Depends(get_shop_service)]


@router.get(
    "",
    response_model=ApiResponse[ShopPage],
    summary="Find partner shops",
    description="Nearby search with `lat`, `lng` and `radius` (meters), text search, rating and "
    "open-now filters, sorting and pagination.",
)
def search_shops(params: ShopSearchQuery, service: Service) -> ApiResponse[ShopPage]:
    return ok(service.search(params))


@router.get("/{shop_id}", response_model=ApiResponse[ShopDetailOut], summary="Shop details")
def get_shop(
    shop_id: uuid.UUID,
    service: Service,
    lat: Annotated[float | None, Query(ge=-90, le=90)] = None,
    lng: Annotated[float | None, Query(ge=-180, le=180)] = None,
) -> ApiResponse[ShopDetailOut]:
    if (lat is None) != (lng is None):
        raise UnprocessableError("Provide both lat and lng.", code="VALIDATION_ERROR")
    return ok(service.detail(shop_id, lat, lng))


@router.get("/{shop_id}/menu", response_model=ApiResponse[MenuOut], summary="Shop menu")
def get_menu(shop_id: uuid.UUID, service: Service) -> ApiResponse[MenuOut]:
    return ok(service.menu(shop_id))

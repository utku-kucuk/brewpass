import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from brewpass_common.responses import ApiResponse, ok
from brewpass_common.security import CurrentPrincipal, Principal, UserRole, require_roles
from commerce_service.api.subscriptions import get_subscription_service
from commerce_service.clients.catalog_client import CatalogClient, get_catalog_client
from commerce_service.db import get_db
from commerce_service.schemas.order import (
    FavoriteIn,
    OrderCreateIn,
    OrderOut,
    OrderPage,
    OrderStatusIn,
    VerifyQrIn,
)
from commerce_service.services.order_service import OrderService
from commerce_service.services.subscription_service import SubscriptionService

router = APIRouter(prefix="/api/v1/orders", tags=["orders"])

Customer = Annotated[Principal, Depends(require_roles(UserRole.CUSTOMER))]
ShopOwner = Annotated[Principal, Depends(require_roles(UserRole.SHOP_OWNER))]


def get_order_service(
    db: Annotated[Session, Depends(get_db)],
    catalog: Annotated[CatalogClient, Depends(get_catalog_client)],
    subscriptions: Annotated[SubscriptionService, Depends(get_subscription_service)],
) -> OrderService:
    return OrderService(db, catalog, subscriptions)


Service = Annotated[OrderService, Depends(get_order_service)]


@router.post(
    "",
    response_model=ApiResponse[OrderOut],
    status_code=201,
    summary="Order a drink",
    description="Uses one credit (or a guest credit) from the active pass and returns a signed "
    "pickup code in `qr_payload`.",
)
def place_order(body: OrderCreateIn, user: Customer, service: Service) -> ApiResponse[OrderOut]:
    return ok(service.place(user.user_id, body))


@router.get("/history", response_model=ApiResponse[OrderPage], summary="My orders")
def order_history(
    user: Customer,
    service: Service,
    favorites: bool = False,
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> ApiResponse[OrderPage]:
    return ok(service.history(user.user_id, favorites_only=favorites, limit=limit, offset=offset))


@router.get(
    "/incoming",
    response_model=ApiResponse[list[OrderOut]],
    summary="Open orders for my shops",
    description="Shop owners: pending to ready orders, priority pickups first, then oldest.",
)
def incoming_orders(owner: ShopOwner, service: Service) -> ApiResponse[list[OrderOut]]:
    return ok(service.incoming(owner.user_id))


@router.post(
    "/verify-qr",
    response_model=ApiResponse[OrderOut],
    summary="Complete pickup by scanning the member's QR code",
)
def verify_qr(body: VerifyQrIn, owner: ShopOwner, service: Service) -> ApiResponse[OrderOut]:
    return ok(service.complete_with_qr(owner.user_id, body.qr_payload))


@router.get("/{order_id}", response_model=ApiResponse[OrderOut], summary="Order details and QR")
def get_order(
    order_id: uuid.UUID, principal: CurrentPrincipal, service: Service
) -> ApiResponse[OrderOut]:
    return ok(service.get_for(principal.user_id, order_id))


@router.patch(
    "/{order_id}/status",
    response_model=ApiResponse[OrderOut],
    summary="Update status (shop owner)",
    description="PENDING → ACCEPTED → PREPARING → READY; PENDING or ACCEPTED → CANCELLED.",
)
def update_status(
    order_id: uuid.UUID, body: OrderStatusIn, owner: ShopOwner, service: Service
) -> ApiResponse[OrderOut]:
    return ok(service.update_status_as_owner(owner.user_id, order_id, body.status))


@router.post(
    "/{order_id}/cancel",
    response_model=ApiResponse[OrderOut],
    summary="Cancel a pending order (credit refunded)",
)
def cancel_order(order_id: uuid.UUID, user: Customer, service: Service) -> ApiResponse[OrderOut]:
    return ok(service.cancel_as_customer(user.user_id, order_id))


@router.post(
    "/{order_id}/reorder",
    response_model=ApiResponse[OrderOut],
    status_code=201,
    summary="Order the same drink again",
)
def reorder(order_id: uuid.UUID, user: Customer, service: Service) -> ApiResponse[OrderOut]:
    return ok(service.reorder(user.user_id, order_id))


@router.patch(
    "/{order_id}/favorite", response_model=ApiResponse[OrderOut], summary="Mark as favourite"
)
def set_favorite(
    order_id: uuid.UUID, body: FavoriteIn, user: Customer, service: Service
) -> ApiResponse[OrderOut]:
    return ok(service.set_favorite(user.user_id, order_id, body.is_favorite))

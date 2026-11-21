"""Orders: one customized drink paid with one subscription credit.

Placing an order
1. Ask the catalog for the product (outside any lock): it must exist, be available, and its shop
   must be active and open.
2. Lock the member's subscription row (`SELECT ... FOR UPDATE`), renew it if its period ended,
   and take one credit (or a guest credit). Bottomless passes are unlimited.
3. Create the order (PENDING) and its first status event in the same transaction.
Concurrent orders on the same pass queue on the row lock, so a credit can never be spent twice.

Status flow
    PENDING -> ACCEPTED -> PREPARING -> READY -> COMPLETED (by scanning the QR code)
    PENDING / ACCEPTED -> CANCELLED (credit refunded if the pass is still in the same period)
"""

import uuid

from sqlalchemy.orm import Session

from brewpass_common.errors import (
    ConflictError,
    ForbiddenError,
    NotFoundError,
    UnprocessableError,
)
from commerce_service.clients.catalog_client import CatalogClient, ProductInfo
from commerce_service.config import get_settings
from commerce_service.models import (
    MilkOption,
    Order,
    OrderStatus,
    OrderStatusEvent,
    Subscription,
    SubscriptionStatus,
)
from commerce_service.qr import InvalidQrError, verify_qr_payload
from commerce_service.repositories.order_repository import OrderRepository
from commerce_service.repositories.subscription_repository import SubscriptionRepository
from commerce_service.schemas.order import OrderCreateIn, OrderOut, OrderPage
from commerce_service.services.subscription_service import SubscriptionService, utcnow

# Transitions a shop owner can make with PATCH /orders/{id}/status.
OWNER_TRANSITIONS: dict[OrderStatus, set[OrderStatus]] = {
    OrderStatus.PENDING: {OrderStatus.ACCEPTED, OrderStatus.CANCELLED},
    OrderStatus.ACCEPTED: {OrderStatus.PREPARING, OrderStatus.CANCELLED},
    OrderStatus.PREPARING: {OrderStatus.READY},
}
CUSTOMER_CANCELLABLE = {OrderStatus.PENDING}


class OrderService:
    def __init__(
        self,
        session: Session,
        catalog: CatalogClient,
        subscriptions: SubscriptionService,
    ) -> None:
        self.session = session
        self.catalog = catalog
        self.subscription_service = subscriptions
        self.subscriptions = SubscriptionRepository(session)
        self.orders = OrderRepository(session)

    # --- Placing orders --------------------------------------------------------------------

    def _check_product(self, product: ProductInfo, data: OrderCreateIn) -> None:
        if not product.shop.is_active:
            raise ConflictError("This shop is not taking orders.", code="SHOP_INACTIVE")
        if get_settings().enforce_opening_hours and not product.shop.is_open_now:
            raise ConflictError("This shop is closed right now.", code="SHOP_CLOSED")
        if not product.is_available:
            raise ConflictError(f"{product.name} is sold out.", code="PRODUCT_UNAVAILABLE")
        if data.milk != MilkOption.NONE and not product.supports_milk:
            raise UnprocessableError(
                f"{product.name} can't be made with milk.", code="INVALID_CUSTOMIZATION"
            )
        if data.extra_shots and not product.supports_extra_shot:
            raise UnprocessableError(
                f"{product.name} can't have extra shots.", code="INVALID_CUSTOMIZATION"
            )

    def _take_credit(self, subscription: Subscription, use_guest_credit: bool) -> None:
        if use_guest_credit:
            if subscription.remaining_guest_credits <= 0:
                raise ConflictError("No guest drinks left this month.", code="NO_GUEST_CREDITS")
            subscription.remaining_guest_credits -= 1
        elif subscription.remaining_credits is not None:
            if subscription.remaining_credits <= 0:
                raise ConflictError("No drinks left this month.", code="NO_CREDITS")
            subscription.remaining_credits -= 1

    def place(self, user_id: uuid.UUID, data: OrderCreateIn) -> OrderOut:
        product = self.catalog.get_product(data.product_id)
        self._check_product(product, data)

        subscription = self.subscriptions.get_live(user_id, lock=True)
        if subscription is None:
            raise NotFoundError("Buy a pass to start ordering.", code="NO_ACTIVE_SUBSCRIPTION")
        self.subscription_service.ensure_current_period(subscription)
        if subscription.status != SubscriptionStatus.ACTIVE:
            self.session.commit()  # keep a renewal that just paused the pass
            raise ConflictError("Your pass is paused.", code="SUBSCRIPTION_PAUSED")

        self._take_credit(subscription, data.use_guest_credit)
        order = Order(
            user_id=user_id,
            shop_id=product.shop.id,
            shop_name=product.shop.name,
            shop_owner_id=product.shop.owner_id,
            product_id=product.id,
            product_name=product.name,
            subscription_id=subscription.id,
            status=OrderStatus.PENDING,
            size=data.size,
            milk=data.milk,
            sugar=data.sugar,
            extra_shots=data.extra_shots,
            note=data.note,
            is_guest=data.use_guest_credit,
            is_priority=subscription.plan.priority_pickup,
        )
        order.status_events.append(
            OrderStatusEvent(from_status=None, to_status=OrderStatus.PENDING, changed_by_id=user_id)
        )
        self.session.add(order)
        self.session.commit()
        return OrderOut.from_order(order)

    def reorder(self, user_id: uuid.UUID, order_id: uuid.UUID) -> OrderOut:
        previous = self._own_order(user_id, order_id)
        return self.place(
            user_id,
            OrderCreateIn(
                product_id=previous.product_id,
                size=previous.size,
                milk=previous.milk,
                sugar=previous.sugar,
                extra_shots=previous.extra_shots,
                note=previous.note,
            ),
        )

    # --- Reading ---------------------------------------------------------------------------

    def _order(self, order_id: uuid.UUID, *, lock: bool = False) -> Order:
        order = self.orders.get(order_id, lock=lock)
        if order is None:
            raise NotFoundError("Order not found.", code="ORDER_NOT_FOUND")
        return order

    def _own_order(self, user_id: uuid.UUID, order_id: uuid.UUID, *, lock: bool = False) -> Order:
        order = self._order(order_id, lock=lock)
        if order.user_id != user_id:
            # Don't reveal that someone else's order exists.
            raise NotFoundError("Order not found.", code="ORDER_NOT_FOUND")
        return order

    def get_for(self, user_id: uuid.UUID, order_id: uuid.UUID) -> OrderOut:
        order = self._order(order_id)
        if user_id not in (order.user_id, order.shop_owner_id):
            raise NotFoundError("Order not found.", code="ORDER_NOT_FOUND")
        return OrderOut.from_order(order)

    def history(
        self, user_id: uuid.UUID, *, favorites_only: bool, limit: int, offset: int
    ) -> OrderPage:
        orders, total = self.orders.history(
            user_id, favorites_only=favorites_only, limit=limit, offset=offset
        )
        return OrderPage(
            items=[OrderOut.from_order(o) for o in orders], total=total, limit=limit, offset=offset
        )

    def incoming(self, owner_id: uuid.UUID) -> list[OrderOut]:
        return [OrderOut.from_order(o) for o in self.orders.incoming_for_owner(owner_id)]

    def set_favorite(self, user_id: uuid.UUID, order_id: uuid.UUID, value: bool) -> OrderOut:
        order = self._own_order(user_id, order_id)
        order.is_favorite = value
        self.session.commit()
        return OrderOut.from_order(order)

    # --- Status changes --------------------------------------------------------------------

    def _transition(self, order: Order, to_status: OrderStatus, actor_id: uuid.UUID) -> None:
        order.status_events.append(
            OrderStatusEvent(from_status=order.status, to_status=to_status, changed_by_id=actor_id)
        )
        order.status = to_status
        if to_status == OrderStatus.COMPLETED:
            order.completed_at = utcnow()
        if to_status == OrderStatus.CANCELLED:
            self._refund(order)

    def _refund(self, order: Order) -> None:
        """Give the credit back if the pass is still live and in the period the order used."""
        subscription = self.session.get(Subscription, order.subscription_id, with_for_update=True)
        if (
            subscription is None
            or subscription.status == SubscriptionStatus.CANCELLED
            or order.created_at < subscription.started_at
        ):
            return
        if order.is_guest:
            subscription.remaining_guest_credits += 1
        elif subscription.remaining_credits is not None:
            subscription.remaining_credits += 1

    def update_status_as_owner(
        self, owner_id: uuid.UUID, order_id: uuid.UUID, to_status: OrderStatus
    ) -> OrderOut:
        order = self._order(order_id, lock=True)
        if order.shop_owner_id != owner_id:
            raise ForbiddenError("This order belongs to another shop.")
        if to_status == OrderStatus.COMPLETED:
            raise ConflictError(
                "Scan the member's QR code to complete pickup.", code="INVALID_STATUS_TRANSITION"
            )
        if to_status not in OWNER_TRANSITIONS.get(order.status, set()):
            raise ConflictError(
                f"An order that is {order.status.value} can't become {to_status.value}.",
                code="INVALID_STATUS_TRANSITION",
            )
        self._transition(order, to_status, owner_id)
        self.session.commit()
        return OrderOut.from_order(order)

    def cancel_as_customer(self, user_id: uuid.UUID, order_id: uuid.UUID) -> OrderOut:
        order = self._own_order(user_id, order_id, lock=True)
        if order.status not in CUSTOMER_CANCELLABLE:
            raise ConflictError(
                "The shop has already started on this order.", code="INVALID_STATUS_TRANSITION"
            )
        self._transition(order, OrderStatus.CANCELLED, user_id)
        self.session.commit()
        return OrderOut.from_order(order)

    def complete_with_qr(self, owner_id: uuid.UUID, raw_payload: str) -> OrderOut:
        try:
            claims = verify_qr_payload(raw_payload)
        except InvalidQrError as exc:
            raise UnprocessableError(str(exc), code="INVALID_QR") from exc

        order = self._order(claims.order_id, lock=True)
        if order.user_id != claims.user_id or order.shop_id != claims.shop_id:
            raise UnprocessableError("QR code does not match this order.", code="INVALID_QR")
        if order.shop_owner_id != owner_id:
            raise ForbiddenError("This order belongs to another shop.", code="WRONG_SHOP")
        if order.status == OrderStatus.COMPLETED:
            raise ConflictError("This order was already picked up.", code="ALREADY_COMPLETED")
        if order.status != OrderStatus.READY:
            raise ConflictError(
                f"The order is {order.status.value}, not READY.", code="ORDER_NOT_READY"
            )
        self._transition(order, OrderStatus.COMPLETED, owner_id)
        self.session.commit()
        return OrderOut.from_order(order)

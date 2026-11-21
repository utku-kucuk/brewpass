import uuid
from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from commerce_service.models import DrinkSize, MilkOption, Order, OrderStatus
from commerce_service.qr import qr_payload


class OrderCreateIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    product_id: uuid.UUID
    size: DrinkSize = DrinkSize.M
    milk: MilkOption = MilkOption.NONE
    sugar: int = Field(default=0, ge=0, le=3, description="Spoons of sugar")
    extra_shots: int = Field(default=0, ge=0, le=3)
    note: Annotated[str, StringConstraints(strip_whitespace=True, max_length=200)] | None = None
    use_guest_credit: bool = Field(
        default=False, description="Pay with a guest drink, e.g. a coffee for a friend."
    )


class OrderStatusIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: OrderStatus = Field(
        description="ACCEPTED, PREPARING, READY or CANCELLED. COMPLETED happens by scanning the QR."
    )


class FavoriteIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    is_favorite: bool


class VerifyQrIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    qr_payload: Annotated[str, StringConstraints(min_length=10, max_length=1000)]


class StatusEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    from_status: OrderStatus | None
    to_status: OrderStatus
    created_at: datetime


class OrderOut(BaseModel):
    id: uuid.UUID
    status: OrderStatus
    shop_id: uuid.UUID
    shop_name: str
    product_id: uuid.UUID
    product_name: str
    size: DrinkSize
    milk: MilkOption
    sugar: int
    extra_shots: int
    note: str | None
    is_guest: bool
    is_priority: bool
    is_favorite: bool
    created_at: datetime
    completed_at: datetime | None
    qr_payload: str | None = Field(
        description="Signed pickup code to render as a QR image; null once the order is closed."
    )
    status_history: list[StatusEventOut]

    @classmethod
    def from_order(cls, order: Order) -> "OrderOut":
        closed = order.status in (OrderStatus.COMPLETED, OrderStatus.CANCELLED)
        return cls(
            id=order.id,
            status=order.status,
            shop_id=order.shop_id,
            shop_name=order.shop_name,
            product_id=order.product_id,
            product_name=order.product_name,
            size=order.size,
            milk=order.milk,
            sugar=order.sugar,
            extra_shots=order.extra_shots,
            note=order.note,
            is_guest=order.is_guest,
            is_priority=order.is_priority,
            is_favorite=order.is_favorite,
            created_at=order.created_at,
            completed_at=order.completed_at,
            qr_payload=None if closed else qr_payload(order),
            status_history=[StatusEventOut.model_validate(e) for e in order.status_events],
        )


class OrderPage(BaseModel):
    items: list[OrderOut]
    total: int
    limit: int
    offset: int

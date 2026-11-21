import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    SmallInteger,
    String,
    false,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from brewpass_common.db import TimestampMixin, UUIDPrimaryKeyMixin
from commerce_service.db import Base
from commerce_service.models.enums import DrinkSize, MilkOption, OrderStatus

ORDER_STATUS_ENUM = Enum(OrderStatus, name="order_status")


class Order(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A single customized drink redeemed against a subscription credit."""

    __tablename__ = "orders"
    __table_args__ = (
        CheckConstraint("sugar BETWEEN 0 AND 3", name="sugar_range"),
        CheckConstraint("extra_shots BETWEEN 0 AND 3", name="extra_shots_range"),
        Index("ix_orders_user_id_created_at", "user_id", "created_at"),
        Index("ix_orders_shop_id_status", "shop_id", "status"),
        Index("ix_orders_shop_owner_id_status", "shop_owner_id", "status"),
    )

    # Ids owned by other services (auth, catalog); no cross-service foreign keys.
    user_id: Mapped[uuid.UUID] = mapped_column()
    shop_id: Mapped[uuid.UUID] = mapped_column()
    product_id: Mapped[uuid.UUID] = mapped_column()
    # Snapshot of catalog data at order time, so history stays readable if the menu changes.
    shop_name: Mapped[str] = mapped_column(String(120))
    # Owner of the shop when the order was placed; authorizes shop-side actions.
    shop_owner_id: Mapped[uuid.UUID | None] = mapped_column()
    product_name: Mapped[str] = mapped_column(String(100))
    subscription_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("subscriptions.id", ondelete="RESTRICT"), index=True
    )
    status: Mapped[OrderStatus] = mapped_column(ORDER_STATUS_ENUM, default=OrderStatus.PENDING)

    # Customization
    size: Mapped[DrinkSize] = mapped_column(Enum(DrinkSize, name="drink_size"), default=DrinkSize.M)
    milk: Mapped[MilkOption] = mapped_column(
        Enum(MilkOption, name="milk_option"), default=MilkOption.NONE
    )
    sugar: Mapped[int] = mapped_column(SmallInteger, default=0)
    extra_shots: Mapped[int] = mapped_column(SmallInteger, default=0)
    note: Mapped[str | None] = mapped_column(String(200))

    # True when paid with a guest credit instead of a regular one.
    is_guest: Mapped[bool] = mapped_column(Boolean, default=False)
    is_favorite: Mapped[bool] = mapped_column(Boolean, default=False)
    # Bottomless members get priority pickup; shops see these first.
    is_priority: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    status_events: Mapped[list["OrderStatusEvent"]] = relationship(
        back_populates="order", cascade="all, delete-orphan", order_by="OrderStatusEvent.created_at"
    )


class OrderStatusEvent(UUIDPrimaryKeyMixin, Base):
    """Audit trail of order status transitions."""

    __tablename__ = "order_status_events"

    order_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"), index=True
    )
    from_status: Mapped[OrderStatus | None] = mapped_column(ORDER_STATUS_ENUM)
    to_status: Mapped[OrderStatus] = mapped_column(ORDER_STATUS_ENUM)
    changed_by_id: Mapped[uuid.UUID | None] = mapped_column()
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        nullable=False,
    )

    order: Mapped[Order] = relationship(back_populates="status_events")

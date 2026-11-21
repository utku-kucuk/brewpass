from decimal import Decimal

from sqlalchemy import Boolean, CheckConstraint, Enum, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from brewpass_common.db import TimestampMixin, UUIDPrimaryKeyMixin
from commerce_service.db import Base
from commerce_service.models.enums import PlanCode


class Plan(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A subscription pass that members can buy (Sip, Daily, Bottomless)."""

    __tablename__ = "plans"
    __table_args__ = (
        CheckConstraint("price >= 0", name="price_non_negative"),
        CheckConstraint(
            "monthly_credits IS NULL OR monthly_credits > 0", name="monthly_credits_positive"
        ),
        CheckConstraint("guest_credits >= 0", name="guest_credits_non_negative"),
    )

    code: Mapped[PlanCode] = mapped_column(Enum(PlanCode, name="plan_code"), unique=True)
    name: Mapped[str] = mapped_column(String(50))
    description: Mapped[str | None] = mapped_column(String(255))
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    currency: Mapped[str] = mapped_column(String(3), default="TRY")
    # NULL means unlimited drinks.
    monthly_credits: Mapped[int | None] = mapped_column(Integer)
    guest_credits: Mapped[int] = mapped_column(Integer, default=0)
    priority_pickup: Mapped[bool] = mapped_column(Boolean, default=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    @property
    def is_unlimited(self) -> bool:
        return self.monthly_credits is None

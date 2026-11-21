import enum
import uuid
from decimal import Decimal

from sqlalchemy import Boolean, CheckConstraint, Enum, ForeignKey, Numeric, SmallInteger, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from brewpass_common.db import TimestampMixin, UUIDPrimaryKeyMixin
from payment_service.db import Base


class PaymentStatus(enum.StrEnum):
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"


class PaymentMethod(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A saved (mock) card. Only display data and an opaque token are kept, never the number."""

    __tablename__ = "payment_methods"

    user_id: Mapped[uuid.UUID] = mapped_column(index=True)
    token: Mapped[str] = mapped_column(String(64), unique=True)
    brand: Mapped[str] = mapped_column(String(20))
    last4: Mapped[str] = mapped_column(String(4))
    exp_month: Mapped[int] = mapped_column(SmallInteger)
    exp_year: Mapped[int] = mapped_column(SmallInteger)
    # Test cards that must always decline keep doing so for recurring charges.
    always_declines: Mapped[bool] = mapped_column(Boolean, default=False)


class Payment(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A BrewPass Pay (mock) payment attempt. Failed attempts are stored too."""

    __tablename__ = "payments"
    __table_args__ = (CheckConstraint("amount >= 0", name="amount_non_negative"),)

    # User id from the auth service (no cross-service foreign key).
    user_id: Mapped[uuid.UUID] = mapped_column(index=True)
    # What was paid for, e.g. "subscription:DAILY".
    description: Mapped[str] = mapped_column(String(120))
    transaction_id: Mapped[uuid.UUID] = mapped_column(unique=True, default=uuid.uuid4)
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    currency: Mapped[str] = mapped_column(String(3), default="TRY")
    status: Mapped[PaymentStatus] = mapped_column(Enum(PaymentStatus, name="payment_status"))
    payment_method_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("payment_methods.id", ondelete="SET NULL")
    )
    card_last4: Mapped[str | None] = mapped_column(String(4))
    failure_reason: Mapped[str | None] = mapped_column(String(255))

    payment_method: Mapped[PaymentMethod | None] = relationship()

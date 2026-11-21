import enum
import uuid
from decimal import Decimal

from sqlalchemy import CheckConstraint, Enum, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from brewpass_common.db import TimestampMixin, UUIDPrimaryKeyMixin
from payment_service.db import Base


class PaymentStatus(enum.StrEnum):
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"


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
    card_last4: Mapped[str | None] = mapped_column(String(4))
    failure_reason: Mapped[str | None] = mapped_column(String(255))

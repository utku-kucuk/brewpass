import uuid
from decimal import Decimal

from sqlalchemy import CheckConstraint, Enum, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import PaymentStatus
from app.models.plan import Plan


class Payment(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A BrewPass Pay (mock) payment attempt. Failed attempts are stored too."""

    __tablename__ = "payments"
    __table_args__ = (CheckConstraint("amount >= 0", name="amount_non_negative"),)

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    plan_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("plans.id", ondelete="SET NULL"))
    transaction_id: Mapped[uuid.UUID] = mapped_column(unique=True, default=uuid.uuid4)
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    currency: Mapped[str] = mapped_column(String(3), default="TRY")
    status: Mapped[PaymentStatus] = mapped_column(Enum(PaymentStatus, name="payment_status"))
    card_last4: Mapped[str | None] = mapped_column(String(4))
    failure_reason: Mapped[str | None] = mapped_column(String(255))

    plan: Mapped[Plan | None] = relationship()

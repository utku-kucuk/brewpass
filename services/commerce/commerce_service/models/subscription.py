import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Enum, ForeignKey, Index, Integer, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from brewpass_common.db import TimestampMixin, UUIDPrimaryKeyMixin
from commerce_service.db import Base
from commerce_service.models.enums import SubscriptionStatus
from commerce_service.models.plan import Plan


class Subscription(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "subscriptions"
    __table_args__ = (
        CheckConstraint(
            "remaining_credits IS NULL OR remaining_credits >= 0",
            name="remaining_credits_non_negative",
        ),
        CheckConstraint(
            "remaining_guest_credits >= 0", name="remaining_guest_credits_non_negative"
        ),
        CheckConstraint("expires_at > started_at", name="period_valid"),
        # A member can have at most one live (active or paused) subscription.
        Index(
            "uq_subscriptions_user_id_live",
            "user_id",
            unique=True,
            postgresql_where=text("status IN ('ACTIVE', 'PAUSED')"),
        ),
    )

    # User id from the auth service (no cross-service foreign key).
    user_id: Mapped[uuid.UUID] = mapped_column(index=True)
    plan_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("plans.id", ondelete="RESTRICT"))
    # Transaction id from the payment service for the payment that started or last changed
    # this subscription.
    payment_transaction_id: Mapped[uuid.UUID | None] = mapped_column()
    # Saved card token from the payment service, used for renewals and upgrades.
    card_token: Mapped[str | None] = mapped_column(String(64))
    # A downgrade takes effect at the next renewal.
    pending_plan_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("plans.id", ondelete="SET NULL")
    )
    status: Mapped[SubscriptionStatus] = mapped_column(
        Enum(SubscriptionStatus, name="subscription_status"), default=SubscriptionStatus.ACTIVE
    )
    # NULL for unlimited plans.
    remaining_credits: Mapped[int | None] = mapped_column(Integer)
    remaining_guest_credits: Mapped[int] = mapped_column(Integer, default=0)
    # Current billing period.
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    plan: Mapped[Plan] = relationship(foreign_keys=[plan_id])
    pending_plan: Mapped[Plan | None] = relationship(foreign_keys=[pending_plan_id])

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Enum, ForeignKey, Index, Integer, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import SubscriptionStatus
from app.models.payment import Payment
from app.models.plan import Plan


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

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    plan_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("plans.id", ondelete="RESTRICT"))
    # Payment that started or last changed this subscription.
    payment_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("payments.id", ondelete="SET NULL")
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

    plan: Mapped[Plan] = relationship()
    payment: Mapped[Payment | None] = relationship()

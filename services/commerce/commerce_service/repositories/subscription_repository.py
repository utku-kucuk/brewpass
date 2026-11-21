import uuid
from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from commerce_service.models import Plan, PlanCode, Subscription, SubscriptionStatus

LIVE_STATUSES = (SubscriptionStatus.ACTIVE, SubscriptionStatus.PAUSED)


class PlanRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list_active(self) -> Sequence[Plan]:
        return self.session.scalars(
            select(Plan).where(Plan.is_active.is_(True)).order_by(Plan.sort_order)
        ).all()

    def get_active_by_code(self, code: PlanCode) -> Plan | None:
        return self.session.scalar(select(Plan).where(Plan.code == code, Plan.is_active.is_(True)))


class SubscriptionRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_live(self, user_id: uuid.UUID, *, lock: bool = False) -> Subscription | None:
        """The user's active or paused subscription (at most one exists)."""
        query = select(Subscription).where(
            Subscription.user_id == user_id, Subscription.status.in_(LIVE_STATUSES)
        )
        if lock:
            query = query.with_for_update()
        return self.session.scalar(query)

    def due_for_renewal(self, now: datetime, limit: int = 100) -> Sequence[Subscription]:
        return self.session.scalars(
            select(Subscription)
            .where(Subscription.status == SubscriptionStatus.ACTIVE, Subscription.expires_at <= now)
            .order_by(Subscription.expires_at)
            .limit(limit)
            .with_for_update(skip_locked=True)
        ).all()

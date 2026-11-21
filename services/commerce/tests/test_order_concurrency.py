"""Two simultaneous orders on a pass with one credit left: exactly one may succeed.

Uses real, separately committed sessions (not the rolled-back test session) so the row lock on
the subscription is actually contended, then cleans up after itself.
"""

import threading
import time
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import Engine, delete, select
from sqlalchemy.orm import Session

from brewpass_common.errors import AppError
from commerce_service.models import Order, Plan, PlanCode, Subscription, SubscriptionStatus
from commerce_service.schemas.order import OrderCreateIn
from commerce_service.seed import seed
from commerce_service.services.order_service import OrderService
from commerce_service.services.subscription_service import SubscriptionService
from tests.fakes import LATTE_ID, FakeCatalog, FakePayments


class SlowSubscriptionService(SubscriptionService):
    """Pauses after the subscription row is read, widening the race window."""

    def ensure_current_period(self, subscription: Subscription) -> None:
        time.sleep(0.3)
        super().ensure_current_period(subscription)


def test_last_credit_cannot_be_spent_twice(engine: Engine) -> None:
    user_id = uuid.uuid4()
    with Session(engine) as session:
        seed(session)
        plan = session.scalar(select(Plan).where(Plan.code == PlanCode.SIP))
        assert plan is not None
        now = datetime.now(UTC)
        subscription = Subscription(
            user_id=user_id,
            plan_id=plan.id,
            status=SubscriptionStatus.ACTIVE,
            remaining_credits=1,
            remaining_guest_credits=0,
            started_at=now,
            expires_at=now + timedelta(days=30),
        )
        session.add(subscription)
        session.commit()
        subscription_id = subscription.id

    barrier = threading.Barrier(2)
    results: list[str] = []

    def place() -> None:
        with Session(engine, expire_on_commit=False) as session:
            service = OrderService(
                session, FakeCatalog(), SlowSubscriptionService(session, FakePayments())
            )
            barrier.wait()
            try:
                service.place(user_id, OrderCreateIn(product_id=LATTE_ID))
                results.append("ok")
            except AppError as exc:
                session.rollback()
                results.append(exc.code)

    try:
        threads = [threading.Thread(target=place) for _ in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=10)

        assert sorted(results) == ["NO_CREDITS", "ok"]
        with Session(engine) as session:
            remaining = session.get(Subscription, subscription_id)
            assert remaining is not None and remaining.remaining_credits == 0
    finally:
        with Session(engine) as session:
            session.execute(delete(Order).where(Order.user_id == user_id))
            session.execute(delete(Subscription).where(Subscription.id == subscription_id))
            session.commit()

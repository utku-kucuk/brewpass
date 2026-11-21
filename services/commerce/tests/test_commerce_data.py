import uuid
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from commerce_service.models import Plan, PlanCode, Subscription, SubscriptionStatus
from commerce_service.seed import seed

USER_ID = uuid.uuid4()


def _plan(session: Session, code: PlanCode) -> Plan:
    plan = session.scalar(select(Plan).where(Plan.code == code))
    assert plan is not None
    return plan


def _subscription(plan: Plan, status: SubscriptionStatus) -> Subscription:
    now = datetime.now(UTC)
    return Subscription(
        user_id=USER_ID,
        plan_id=plan.id,
        status=status,
        remaining_credits=plan.monthly_credits,
        remaining_guest_credits=plan.guest_credits,
        started_at=now,
        expires_at=now + timedelta(days=30),
    )


def test_seed_creates_three_plans_idempotently(db_session: Session) -> None:
    seed(db_session)
    seed(db_session)

    assert db_session.scalar(select(func.count()).select_from(Plan)) == 3


def test_bottomless_plan_is_unlimited(db_session: Session) -> None:
    seed(db_session)

    plan = _plan(db_session, PlanCode.BOTTOMLESS)

    assert plan.is_unlimited
    assert plan.guest_credits == 5


def test_user_can_have_only_one_live_subscription(db_session: Session) -> None:
    seed(db_session)
    plan = _plan(db_session, PlanCode.SIP)

    db_session.add(_subscription(plan, SubscriptionStatus.CANCELLED))
    db_session.add(_subscription(plan, SubscriptionStatus.ACTIVE))
    db_session.flush()

    db_session.add(_subscription(plan, SubscriptionStatus.ACTIVE))
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_negative_credits_are_rejected(db_session: Session) -> None:
    seed(db_session)
    subscription = _subscription(_plan(db_session, PlanCode.SIP), SubscriptionStatus.ACTIVE)
    subscription.remaining_credits = -1
    db_session.add(subscription)

    with pytest.raises(IntegrityError):
        db_session.flush()


def test_health_checks_database(client: TestClient) -> None:
    assert client.get("/health").json()["data"]["database"] == "ok"

from datetime import UTC, datetime, timedelta

import pytest
from geoalchemy2 import WKTElement
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.seed import SHOPS, seed
from app.models import Plan, Product, Shop, Subscription, User
from app.models.enums import PlanCode, SubscriptionStatus


def test_seed_creates_minimum_data_and_is_idempotent(db_session: Session) -> None:
    seed(db_session)
    seed(db_session)

    assert db_session.scalar(select(func.count()).select_from(Plan)) == 3
    assert db_session.scalar(select(func.count()).select_from(Shop)) == len(SHOPS) >= 5
    assert db_session.scalar(select(func.count()).select_from(Product)) >= 10


def test_bottomless_plan_is_unlimited(db_session: Session) -> None:
    seed(db_session)

    plan = db_session.scalar(select(Plan).where(Plan.code == PlanCode.BOTTOMLESS))

    assert plan is not None
    assert plan.is_unlimited
    assert plan.guest_credits == 5


def test_postgis_radius_query_orders_shops_by_distance(db_session: Session) -> None:
    seed(db_session)
    # Karaköy pier
    here = WKTElement("POINT(28.9765 41.0222)", srid=4326)
    distance = func.ST_Distance(Shop.location, here)

    rows = db_session.execute(
        select(Shop.name, distance.label("meters"))
        .where(func.ST_DWithin(Shop.location, here, 1500))
        .order_by(distance)
    ).all()

    assert rows[0].name == "Karaköy Brew Lab"
    assert all(row.meters <= 1500 for row in rows)
    assert "Levent Daily Grind" not in {row.name for row in rows}


def _subscription(user: User, plan: Plan, status: SubscriptionStatus) -> Subscription:
    now = datetime.now(UTC)
    return Subscription(
        user_id=user.id,
        plan_id=plan.id,
        status=status,
        remaining_credits=plan.monthly_credits,
        remaining_guest_credits=plan.guest_credits,
        started_at=now,
        expires_at=now + timedelta(days=30),
    )


def test_user_can_have_only_one_live_subscription(db_session: Session) -> None:
    seed(db_session)
    user = db_session.scalar(select(User).where(User.phone_number == "+905550000100"))
    plan = db_session.scalar(select(Plan).where(Plan.code == PlanCode.SIP))
    assert user is not None and plan is not None

    db_session.add(_subscription(user, plan, SubscriptionStatus.CANCELLED))
    db_session.add(_subscription(user, plan, SubscriptionStatus.ACTIVE))
    db_session.flush()

    db_session.add(_subscription(user, plan, SubscriptionStatus.ACTIVE))
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_negative_credits_are_rejected(db_session: Session) -> None:
    seed(db_session)
    user = db_session.scalar(select(User).where(User.phone_number == "+905550000100"))
    plan = db_session.scalar(select(Plan).where(Plan.code == PlanCode.SIP))
    assert user is not None and plan is not None

    subscription = _subscription(user, plan, SubscriptionStatus.ACTIVE)
    subscription.remaining_credits = -1
    db_session.add(subscription)

    with pytest.raises(IntegrityError):
        db_session.flush()

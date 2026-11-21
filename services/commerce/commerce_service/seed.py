"""Idempotent seed: the three subscription passes. Run with: `python -m commerce_service.seed`"""

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from commerce_service.db import SessionLocal
from commerce_service.models import Plan, PlanCode

PLANS = [
    {
        "code": PlanCode.SIP,
        "name": "Sip",
        "description": "10 drinks a month at every partner shop.",
        "price": Decimal("89.99"),
        "monthly_credits": 10,
        "guest_credits": 0,
        "priority_pickup": False,
        "sort_order": 1,
    },
    {
        "code": PlanCode.DAILY,
        "name": "Daily",
        "description": "20 drinks a month plus 2 drinks for friends.",
        "price": Decimal("149.99"),
        "monthly_credits": 20,
        "guest_credits": 2,
        "priority_pickup": False,
        "sort_order": 2,
    },
    {
        "code": PlanCode.BOTTOMLESS,
        "name": "Bottomless",
        "description": "Unlimited drinks, 5 guest drinks and priority pickup.",
        "price": Decimal("249.99"),
        "monthly_credits": None,
        "guest_credits": 5,
        "priority_pickup": True,
        "sort_order": 3,
    },
]


def seed(session: Session) -> None:
    for data in PLANS:
        plan = session.scalar(select(Plan).where(Plan.code == data["code"]))
        if plan is None:
            plan = Plan(code=data["code"])
            session.add(plan)
        for key, value in data.items():
            setattr(plan, key, value)
    session.commit()


def main() -> None:
    with SessionLocal() as session:
        seed(session)
    print(f"Commerce seed complete: plans={len(PLANS)}")


if __name__ == "__main__":
    main()

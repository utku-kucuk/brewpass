import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from brewpass_common.testing import bearer, make_access_token
from commerce_service.models import Subscription
from commerce_service.services.subscription_service import add_month
from tests.conftest import INTERNAL_TOKEN, KEYS
from tests.fakes import FakePayments

BASE = "/api/v1/subscriptions"
ME = f"{BASE}/me"
USER_ID = uuid.uuid4()
AUTH = bearer(make_access_token(KEYS.private_pem, USER_ID))
NEXT_YEAR = datetime.now(UTC).year + 1


def card(number: str = "4242424242424242") -> dict[str, Any]:
    return {
        "number": number,
        "exp_month": 12,
        "exp_year": NEXT_YEAR,
        "cvc": "123",
        "holder_name": "Zeynep Arslan",
    }


def subscribe(client: TestClient, plan_code: str = "DAILY", **kwargs: Any) -> Any:
    return client.post(BASE, headers=AUTH, json={"plan_code": plan_code, "card": card(**kwargs)})


def expire_period(db_session: Session) -> None:
    """Move the current period into the past so the next read renews it."""
    subscription = db_session.scalar(select(Subscription).where(Subscription.user_id == USER_ID))
    assert subscription is not None
    subscription.started_at = datetime.now(UTC) - timedelta(days=31)
    subscription.expires_at = datetime.now(UTC) - timedelta(minutes=1)
    db_session.flush()


# --- Plans ---------------------------------------------------------------------------------


def test_plans_are_public_and_sorted(client: TestClient) -> None:
    response = client.get(f"{BASE}/plans")

    assert response.status_code == 200
    plans = response.json()["data"]
    assert [p["code"] for p in plans] == ["SIP", "DAILY", "BOTTOMLESS"]
    assert plans[2]["is_unlimited"] is True
    assert plans[2]["monthly_credits"] is None
    assert plans[1]["price"] == "149.99"


# --- Subscribe -----------------------------------------------------------------------------


def test_subscribe_charges_plan_price_and_starts_monthly_period(
    client: TestClient, payments: FakePayments
) -> None:
    response = subscribe(client)

    assert response.status_code == 201
    data = response.json()["data"]
    assert data["status"] == "ACTIVE"
    assert data["plan"]["code"] == "DAILY"
    assert data["remaining_credits"] == 20
    assert data["remaining_guest_credits"] == 2
    assert data["payment_transaction_id"]
    start = datetime.fromisoformat(data["current_period_start"])
    assert datetime.fromisoformat(data["current_period_end"]) == add_month(start)

    assert payments.last.amount == Decimal("149.99")
    assert payments.last.description == "subscription:DAILY"
    assert payments.last.card is not None and payments.last.card["number"] == "4242424242424242"


def test_second_subscription_is_rejected_without_charging(
    client: TestClient, payments: FakePayments
) -> None:
    subscribe(client)

    response = subscribe(client, "SIP")

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "SUBSCRIPTION_EXISTS"
    assert len(payments.charges) == 1


def test_declined_payment_creates_no_subscription(client: TestClient) -> None:
    response = subscribe(client, number="4000000000000002")

    assert response.status_code == 402
    assert response.json()["error"]["code"] == "PAYMENT_DECLINED"
    assert client.get(ME, headers=AUTH).json()["error"]["code"] == "NO_ACTIVE_SUBSCRIPTION"


def test_payment_service_down_returns_503(client: TestClient, payments: FakePayments) -> None:
    payments.unavailable = True

    response = subscribe(client)

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "SERVICE_UNAVAILABLE"


def test_card_number_is_not_echoed_in_validation_errors(client: TestClient) -> None:
    response = client.post(
        BASE, headers=AUTH, json={"plan_code": "GOLD", "card": card("4242424242424242")}
    )

    assert response.status_code == 422
    assert "4242424242424242" not in response.text


def test_only_customers_can_subscribe(client: TestClient) -> None:
    owner = bearer(make_access_token(KEYS.private_pem, uuid.uuid4(), "SHOP_OWNER"))

    assert client.post(BASE, json={"plan_code": "SIP", "card": card()}).status_code == 401
    response = client.post(BASE, headers=owner, json={"plan_code": "SIP", "card": card()})
    assert response.status_code == 403


# --- Renewal -------------------------------------------------------------------------------


def test_expired_period_renews_with_saved_card(
    client: TestClient, db_session: Session, payments: FakePayments
) -> None:
    subscribe(client)
    expire_period(db_session)

    data = client.get(ME, headers=AUTH).json()["data"]

    assert data["status"] == "ACTIVE"
    assert datetime.fromisoformat(data["current_period_end"]) > datetime.now(UTC)
    assert data["remaining_credits"] == 20
    assert payments.last.description == "renewal:DAILY"
    assert payments.last.card_token == "pm_test_1"


def test_declined_renewal_pauses_and_resume_reactivates(
    client: TestClient, db_session: Session, payments: FakePayments
) -> None:
    subscribe(client)
    expire_period(db_session)
    payments.decline = True

    paused = client.get(ME, headers=AUTH).json()["data"]
    payments.decline = False
    resumed = client.post(f"{ME}/resume", headers=AUTH, json={"card": card("5555555555554444")})

    assert paused["status"] == "PAUSED"
    assert resumed.status_code == 200
    assert resumed.json()["data"]["status"] == "ACTIVE"
    assert payments.last.description == "resume:DAILY"


def test_resume_requires_a_paused_pass(client: TestClient) -> None:
    subscribe(client)

    response = client.post(f"{ME}/resume", headers=AUTH, json={})

    assert response.json()["error"]["code"] == "SUBSCRIPTION_NOT_PAUSED"


def test_internal_bulk_renewal(
    client: TestClient, db_session: Session, payments: FakePayments
) -> None:
    subscribe(client)
    expire_period(db_session)

    response = client.post(
        "/internal/subscriptions/renew-due", headers={"X-Internal-Token": INTERNAL_TOKEN}
    )

    assert response.json()["data"] == {"renewed": 1, "paused": 0}
    assert payments.last.description == "renewal:DAILY"


# --- Plan changes --------------------------------------------------------------------------


def test_upgrade_charges_difference_and_adds_credits(
    client: TestClient, db_session: Session, payments: FakePayments
) -> None:
    subscribe(client, "SIP")
    subscription = db_session.scalar(select(Subscription))
    assert subscription is not None
    subscription.remaining_credits = 7  # three drinks already used
    db_session.flush()

    data = client.patch(ME, headers=AUTH, json={"plan_code": "DAILY"}).json()["data"]

    assert data["plan"]["code"] == "DAILY"
    assert data["remaining_credits"] == 17
    assert data["remaining_guest_credits"] == 2
    assert payments.last.amount == Decimal("60.00")
    assert payments.last.description == "upgrade:SIP->DAILY"


def test_upgrade_to_bottomless_is_unlimited(client: TestClient) -> None:
    subscribe(client)

    data = client.patch(ME, headers=AUTH, json={"plan_code": "BOTTOMLESS"}).json()["data"]

    assert data["remaining_credits"] is None
    assert data["remaining_guest_credits"] == 5


def test_declined_upgrade_keeps_current_plan(client: TestClient, payments: FakePayments) -> None:
    subscribe(client)
    payments.decline = True

    response = client.patch(ME, headers=AUTH, json={"plan_code": "BOTTOMLESS"})

    assert response.status_code == 402
    assert client.get(ME, headers=AUTH).json()["data"]["plan"]["code"] == "DAILY"


def test_downgrade_is_scheduled_for_next_period(
    client: TestClient, db_session: Session, payments: FakePayments
) -> None:
    subscribe(client)

    scheduled = client.patch(ME, headers=AUTH, json={"plan_code": "SIP"}).json()["data"]
    expire_period(db_session)
    renewed = client.get(ME, headers=AUTH).json()["data"]

    assert scheduled["plan"]["code"] == "DAILY"
    assert scheduled["pending_plan"]["code"] == "SIP"
    assert renewed["plan"]["code"] == "SIP"
    assert renewed["pending_plan"] is None
    assert renewed["remaining_credits"] == 10
    assert payments.last.amount == Decimal("89.99")


def test_choosing_current_plan_cancels_scheduled_downgrade(client: TestClient) -> None:
    subscribe(client)
    client.patch(ME, headers=AUTH, json={"plan_code": "SIP"})

    data = client.patch(ME, headers=AUTH, json={"plan_code": "DAILY"}).json()["data"]

    assert data["pending_plan"] is None


def test_same_plan_is_rejected(client: TestClient) -> None:
    subscribe(client)

    response = client.patch(ME, headers=AUTH, json={"plan_code": "DAILY"})

    assert response.json()["error"]["code"] == "SAME_PLAN"


def test_paused_pass_cannot_change_plan(
    client: TestClient, db_session: Session, payments: FakePayments
) -> None:
    subscribe(client)
    expire_period(db_session)
    payments.decline = True

    response = client.patch(ME, headers=AUTH, json={"plan_code": "BOTTOMLESS"})

    assert response.json()["error"]["code"] == "SUBSCRIPTION_PAUSED"


# --- Cancel --------------------------------------------------------------------------------


def test_cancel_ends_pass_and_allows_new_subscription(client: TestClient) -> None:
    subscribe(client)

    cancelled = client.delete(ME, headers=AUTH).json()["data"]

    assert cancelled["status"] == "CANCELLED"
    assert cancelled["cancelled_at"]
    assert client.get(ME, headers=AUTH).status_code == 404
    assert subscribe(client, "SIP").status_code == 201


def test_cancel_without_pass_is_not_found(client: TestClient) -> None:
    assert client.delete(ME, headers=AUTH).status_code == 404


# --- Helpers -------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("start", "end"),
    [
        (datetime(2026, 1, 31, tzinfo=UTC), datetime(2026, 2, 28, tzinfo=UTC)),
        (datetime(2028, 1, 31, tzinfo=UTC), datetime(2028, 2, 29, tzinfo=UTC)),
        (datetime(2026, 12, 15, tzinfo=UTC), datetime(2027, 1, 15, tzinfo=UTC)),
    ],
)
def test_add_month(start: datetime, end: datetime) -> None:
    assert add_month(start) == end

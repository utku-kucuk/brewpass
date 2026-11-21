import uuid
from datetime import UTC, datetime
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from brewpass_common.testing import bearer, make_access_token
from payment_service.models import Payment, PaymentMethod, PaymentStatus
from payment_service.schemas.payment import luhn_valid
from tests.conftest import INTERNAL_TOKEN, KEYS

CHARGE = "/internal/payments/charge"
INTERNAL = {"X-Internal-Token": INTERNAL_TOKEN}
USER_ID = uuid.uuid4()
NEXT_YEAR = datetime.now(UTC).year + 1


def card(number: str = "4242 4242 4242 4242", **overrides: Any) -> dict[str, Any]:
    return {
        "number": number,
        "exp_month": 12,
        "exp_year": NEXT_YEAR,
        "cvc": "123",
        "holder_name": "Zeynep Arslan",
        **overrides,
    }


def charge_body(**overrides: Any) -> dict[str, Any]:
    return {
        "user_id": str(USER_ID),
        "amount": "149.99",
        "description": "subscription:DAILY",
        "card": card(),
        **overrides,
    }


# --- Card validation -----------------------------------------------------------------------


@pytest.mark.parametrize(
    ("number", "valid"),
    [("4242424242424242", True), ("4000000000000002", True), ("4242424242424241", False)],
)
def test_luhn(number: str, valid: bool) -> None:
    assert luhn_valid(number) is valid


@pytest.mark.parametrize(
    ("overrides", "field"),
    [
        ({"number": "4242 4242 4242 4241"}, "card.number"),
        ({"number": "1234"}, "card.number"),
        ({"cvc": "12"}, "card.cvc"),
        ({"cvc": "12a"}, "card.cvc"),
        ({"exp_month": 13}, "card.exp_month"),
        ({"exp_year": 2020}, "card"),
    ],
    ids=["luhn", "too-short", "cvc-short", "cvc-letters", "month", "expired"],
)
def test_invalid_cards_are_rejected_without_echoing_the_number(
    client: TestClient, overrides: dict[str, Any], field: str
) -> None:
    response = client.post(CHARGE, headers=INTERNAL, json=charge_body(card=card(**overrides)))

    assert response.status_code == 422
    assert response.json()["error"]["details"][0]["field"] == field
    assert "4242" not in response.text


def test_card_or_token_is_required(client: TestClient) -> None:
    response = client.post(CHARGE, headers=INTERNAL, json=charge_body(card=None))

    assert response.status_code == 422


# --- Charging ------------------------------------------------------------------------------


def test_successful_charge_saves_card_without_number(
    client: TestClient, db_session: Session
) -> None:
    response = client.post(CHARGE, headers=INTERNAL, json=charge_body())

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["status"] == "SUCCEEDED"
    assert data["amount"] == "149.99"
    assert data["card_last4"] == "4242"
    assert data["card_brand"] == "VISA"
    assert data["card_token"].startswith("pm_")

    method = db_session.scalar(select(PaymentMethod))
    assert method is not None and method.last4 == "4242"
    assert "4242424242424242" not in str(vars(method))


def test_declining_test_card_returns_402_and_records_failure(
    client: TestClient, db_session: Session
) -> None:
    response = client.post(
        CHARGE, headers=INTERNAL, json=charge_body(card=card("4000 0000 0000 0002"))
    )

    assert response.status_code == 402
    error = response.json()["error"]
    assert error["code"] == "PAYMENT_DECLINED"
    payment = db_session.scalar(select(Payment))
    assert payment is not None
    assert payment.status == PaymentStatus.FAILED
    assert str(payment.transaction_id) == error["details"]["transaction_id"]


def test_saved_card_token_can_be_charged_again(client: TestClient) -> None:
    token = client.post(CHARGE, headers=INTERNAL, json=charge_body()).json()["data"]["card_token"]

    response = client.post(
        CHARGE, headers=INTERNAL, json=charge_body(card=None, card_token=token, amount="60.00")
    )

    assert response.status_code == 200
    assert response.json()["data"]["card_token"] == token


def test_saved_declining_card_keeps_declining(client: TestClient, db_session: Session) -> None:
    client.post(CHARGE, headers=INTERNAL, json=charge_body(card=card("4000 0000 0000 0002")))
    method = db_session.scalar(select(PaymentMethod))
    assert method is not None

    response = client.post(
        CHARGE, headers=INTERNAL, json=charge_body(card=None, card_token=method.token)
    )

    assert response.status_code == 402


def test_card_token_of_another_user_is_not_found(client: TestClient) -> None:
    token = client.post(CHARGE, headers=INTERNAL, json=charge_body()).json()["data"]["card_token"]

    response = client.post(
        CHARGE,
        headers=INTERNAL,
        json=charge_body(user_id=str(uuid.uuid4()), card=None, card_token=token),
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "PAYMENT_METHOD_NOT_FOUND"


def test_charge_requires_internal_token(client: TestClient) -> None:
    assert client.post(CHARGE, json=charge_body()).status_code == 401


# --- History -------------------------------------------------------------------------------


def test_history_lists_only_my_payments_newest_first(client: TestClient) -> None:
    client.post(CHARGE, headers=INTERNAL, json=charge_body(amount="89.99"))
    client.post(CHARGE, headers=INTERNAL, json=charge_body(card=card("4000000000000002")))
    client.post(CHARGE, headers=INTERNAL, json=charge_body(user_id=str(uuid.uuid4())))

    response = client.get(
        "/api/v1/payments/me", headers=bearer(make_access_token(KEYS.private_pem, USER_ID))
    )

    assert response.status_code == 200
    payments = response.json()["data"]
    assert [p["status"] for p in payments] == ["FAILED", "SUCCEEDED"]
    assert payments[0]["failure_reason"] == "Card declined by the issuer."
    assert payments[1]["amount"] == "89.99"


def test_history_requires_sign_in(client: TestClient) -> None:
    assert client.get("/api/v1/payments/me").status_code == 401

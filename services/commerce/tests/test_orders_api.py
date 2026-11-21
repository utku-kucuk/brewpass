import json
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from brewpass_common.testing import bearer, make_access_token
from commerce_service.models import Order, Subscription
from commerce_service.qr import verify_qr_payload
from tests.conftest import KEYS
from tests.fakes import LATTE_ID, OWNER_ID, SHOP_ID, TEA_ID, FakeCatalog, FakePayments

ORDERS = "/api/v1/orders"
USER_ID = uuid.uuid4()
AUTH = bearer(make_access_token(KEYS.private_pem, USER_ID))
OWNER = bearer(make_access_token(KEYS.private_pem, OWNER_ID, "SHOP_OWNER"))
OTHER_OWNER = bearer(make_access_token(KEYS.private_pem, uuid.uuid4(), "SHOP_OWNER"))
NEXT_YEAR = datetime.now(UTC).year + 1


def buy_pass(client: TestClient, plan_code: str = "SIP") -> None:
    card = {
        "number": "4242424242424242",
        "exp_month": 12,
        "exp_year": NEXT_YEAR,
        "cvc": "123",
        "holder_name": "Zeynep Arslan",
    }
    response = client.post(
        "/api/v1/subscriptions", headers=AUTH, json={"plan_code": plan_code, "card": card}
    )
    assert response.status_code == 201, response.text


def order(client: TestClient, **body: Any) -> Any:
    return client.post(ORDERS, headers=AUTH, json={"product_id": str(LATTE_ID), **body})


def credits(client: TestClient) -> Any:
    return client.get("/api/v1/subscriptions/me", headers=AUTH).json()["data"]["remaining_credits"]


def set_status(client: TestClient, order_id: str, status: str, headers: Any = OWNER) -> Any:
    return client.patch(f"{ORDERS}/{order_id}/status", headers=headers, json={"status": status})


def make_ready(client: TestClient) -> dict[str, Any]:
    placed = order(client).json()["data"]
    for status in ("ACCEPTED", "PREPARING", "READY"):
        assert set_status(client, placed["id"], status).status_code == 200
    return client.get(f"{ORDERS}/{placed['id']}", headers=AUTH).json()["data"]


# --- Placing orders ------------------------------------------------------------------------


def test_order_uses_one_credit_and_returns_signed_qr(client: TestClient) -> None:
    buy_pass(client)

    response = order(client, size="L", milk="OAT", sugar=1, extra_shots=1, note="Extra hot")

    assert response.status_code == 201
    data = response.json()["data"]
    assert data["status"] == "PENDING"
    assert (data["product_name"], data["shop_name"]) == ("Caffè Latte", "Moda Roastery")
    assert (data["size"], data["milk"], data["sugar"], data["extra_shots"]) == ("L", "OAT", 1, 1)
    assert data["status_history"][0]["to_status"] == "PENDING"
    assert credits(client) == 9

    claims = verify_qr_payload(data["qr_payload"])
    assert (claims.order_id, claims.user_id, claims.shop_id) == (
        uuid.UUID(data["id"]),
        USER_ID,
        SHOP_ID,
    )


def test_order_without_pass_is_rejected(client: TestClient) -> None:
    response = order(client)

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NO_ACTIVE_SUBSCRIPTION"


def test_last_credit_then_no_credits(client: TestClient, db_session: Session) -> None:
    buy_pass(client)
    subscription = db_session.scalar(select(Subscription))
    assert subscription is not None
    subscription.remaining_credits = 1
    db_session.flush()

    first, second = order(client), order(client)

    assert first.status_code == 201
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "NO_CREDITS"
    assert credits(client) == 0


def test_bottomless_is_unlimited_and_priority(client: TestClient) -> None:
    buy_pass(client, "BOTTOMLESS")

    responses = [order(client) for _ in range(3)]

    assert all(r.status_code == 201 for r in responses)
    assert all(r.json()["data"]["is_priority"] for r in responses)
    assert credits(client) is None


def test_guest_credit(client: TestClient) -> None:
    buy_pass(client, "DAILY")  # 2 guest drinks

    responses = [order(client, use_guest_credit=True) for _ in range(3)]

    assert [r.status_code for r in responses] == [201, 201, 409]
    assert responses[2].json()["error"]["code"] == "NO_GUEST_CREDITS"
    assert credits(client) == 20  # regular credits untouched


@pytest.mark.parametrize(
    ("setup", "code", "status"),
    [
        (lambda c: setattr(c, "shop_open", False), "SHOP_CLOSED", 409),
        (lambda c: setattr(c, "shop_active", False), "SHOP_INACTIVE", 409),
        (lambda c: c.sold_out.add(LATTE_ID), "PRODUCT_UNAVAILABLE", 409),
        (lambda c: setattr(c, "unavailable", True), "SERVICE_UNAVAILABLE", 503),
    ],
    ids=["closed", "inactive", "sold-out", "catalog-down"],
)
def test_order_rejected_when_catalog_says_no(
    client: TestClient, catalog: FakeCatalog, setup: Any, code: str, status: int
) -> None:
    buy_pass(client)
    setup(catalog)

    response = order(client)

    assert response.status_code == status
    assert response.json()["error"]["code"] == code
    assert credits(client) == 10  # nothing was taken


def test_unknown_product(client: TestClient) -> None:
    buy_pass(client)

    response = client.post(ORDERS, headers=AUTH, json={"product_id": str(uuid.uuid4())})

    assert response.json()["error"]["code"] == "PRODUCT_NOT_FOUND"


@pytest.mark.parametrize("body", [{"milk": "OAT"}, {"extra_shots": 1}])
def test_customization_must_match_the_drink(client: TestClient, body: dict) -> None:
    buy_pass(client)

    response = client.post(ORDERS, headers=AUTH, json={"product_id": str(TEA_ID), **body})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_CUSTOMIZATION"


@pytest.mark.parametrize("body", [{"sugar": 4}, {"extra_shots": -1}, {"size": "XL"}])
def test_customization_ranges(client: TestClient, body: dict) -> None:
    buy_pass(client)

    assert order(client, **body).status_code == 422


def test_expired_pass_renews_before_ordering(
    client: TestClient, db_session: Session, payments: FakePayments
) -> None:
    buy_pass(client)
    subscription = db_session.scalar(select(Subscription))
    assert subscription is not None
    subscription.remaining_credits = 0
    subscription.started_at = datetime.now(UTC) - timedelta(days=31)
    subscription.expires_at = datetime.now(UTC) - timedelta(minutes=1)
    db_session.flush()

    response = order(client)

    assert response.status_code == 201
    assert payments.last.description == "renewal:SIP"
    assert credits(client) == 9


def test_shop_owners_cannot_order(client: TestClient) -> None:
    response = client.post(ORDERS, headers=OWNER, json={"product_id": str(LATTE_ID)})

    assert response.status_code == 403


# --- Status flow and QR pickup -------------------------------------------------------------


def test_full_flow_to_pickup(client: TestClient) -> None:
    buy_pass(client)
    ready = make_ready(client)

    response = client.post(
        f"{ORDERS}/verify-qr", headers=OWNER, json={"qr_payload": ready["qr_payload"]}
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["status"] == "COMPLETED"
    assert data["completed_at"]
    assert data["qr_payload"] is None
    assert [e["to_status"] for e in data["status_history"]] == [
        "PENDING",
        "ACCEPTED",
        "PREPARING",
        "READY",
        "COMPLETED",
    ]


def test_qr_cannot_be_used_twice(client: TestClient) -> None:
    buy_pass(client)
    qr = make_ready(client)["qr_payload"]
    client.post(f"{ORDERS}/verify-qr", headers=OWNER, json={"qr_payload": qr})

    response = client.post(f"{ORDERS}/verify-qr", headers=OWNER, json={"qr_payload": qr})

    assert response.json()["error"]["code"] == "ALREADY_COMPLETED"


def test_tampered_qr_is_rejected(client: TestClient) -> None:
    buy_pass(client)
    payload = json.loads(make_ready(client)["qr_payload"])
    payload["user_id"] = str(uuid.uuid4())

    response = client.post(
        f"{ORDERS}/verify-qr", headers=OWNER, json={"qr_payload": json.dumps(payload)}
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_QR"


@pytest.mark.parametrize("raw", ["not json at all", '{"order_id": "x", "signature": "y"}'])
def test_garbage_qr_is_rejected(client: TestClient, raw: str) -> None:
    response = client.post(f"{ORDERS}/verify-qr", headers=OWNER, json={"qr_payload": raw})

    assert response.json()["error"]["code"] == "INVALID_QR"


def test_qr_before_ready_is_rejected(client: TestClient) -> None:
    buy_pass(client)
    qr = order(client).json()["data"]["qr_payload"]

    response = client.post(f"{ORDERS}/verify-qr", headers=OWNER, json={"qr_payload": qr})

    assert response.json()["error"]["code"] == "ORDER_NOT_READY"


def test_other_shops_cannot_scan_or_update(client: TestClient) -> None:
    buy_pass(client)
    placed = order(client).json()["data"]

    scan = client.post(
        f"{ORDERS}/verify-qr", headers=OTHER_OWNER, json={"qr_payload": placed["qr_payload"]}
    )
    update = set_status(client, placed["id"], "ACCEPTED", OTHER_OWNER)

    assert scan.status_code == 403
    assert update.status_code == 403


@pytest.mark.parametrize(
    ("path", "target"),
    [([], "READY"), ([], "COMPLETED"), (["ACCEPTED", "PREPARING"], "CANCELLED")],
    ids=["skip-steps", "complete-without-qr", "cancel-while-preparing"],
)
def test_invalid_transitions(client: TestClient, path: list[str], target: str) -> None:
    buy_pass(client)
    order_id = order(client).json()["data"]["id"]
    for status in path:
        set_status(client, order_id, status)

    response = set_status(client, order_id, target)

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "INVALID_STATUS_TRANSITION"


def test_shop_cancellation_refunds_credit(client: TestClient) -> None:
    buy_pass(client)
    order_id = order(client).json()["data"]["id"]
    set_status(client, order_id, "ACCEPTED")

    response = set_status(client, order_id, "CANCELLED")

    assert response.json()["data"]["status"] == "CANCELLED"
    assert credits(client) == 10


def test_customer_can_cancel_only_pending_orders(client: TestClient) -> None:
    buy_pass(client)
    first = order(client).json()["data"]["id"]
    second = order(client).json()["data"]["id"]
    set_status(client, second, "ACCEPTED")

    cancelled = client.post(f"{ORDERS}/{first}/cancel", headers=AUTH)
    too_late = client.post(f"{ORDERS}/{second}/cancel", headers=AUTH)

    assert cancelled.json()["data"]["status"] == "CANCELLED"
    assert too_late.json()["error"]["code"] == "INVALID_STATUS_TRANSITION"
    assert credits(client) == 9


def test_guest_cancellation_refunds_guest_credit(client: TestClient) -> None:
    buy_pass(client, "DAILY")
    order_id = order(client, use_guest_credit=True).json()["data"]["id"]

    client.post(f"{ORDERS}/{order_id}/cancel", headers=AUTH)

    sub = client.get("/api/v1/subscriptions/me", headers=AUTH).json()["data"]
    assert sub["remaining_guest_credits"] == 2


def test_no_refund_after_period_rolled_over(client: TestClient, db_session: Session) -> None:
    buy_pass(client)
    order_id = order(client).json()["data"]["id"]
    placed = db_session.get(Order, uuid.UUID(order_id))
    assert placed is not None
    placed.created_at = datetime.now(UTC) - timedelta(days=40)
    db_session.flush()

    client.post(f"{ORDERS}/{order_id}/cancel", headers=AUTH)

    assert credits(client) == 9


# --- Reading, favourites, reorder ----------------------------------------------------------


def test_incoming_lists_open_orders_with_priority_first(client: TestClient) -> None:
    buy_pass(client)
    normal = order(client).json()["data"]["id"]
    done = make_ready(client)
    client.post(f"{ORDERS}/verify-qr", headers=OWNER, json={"qr_payload": done["qr_payload"]})
    client.patch("/api/v1/subscriptions/me", headers=AUTH, json={"plan_code": "BOTTOMLESS"})
    priority = order(client).json()["data"]["id"]

    incoming = client.get(f"{ORDERS}/incoming", headers=OWNER).json()["data"]

    assert [o["id"] for o in incoming] == [priority, normal]
    assert client.get(f"{ORDERS}/incoming", headers=OTHER_OWNER).json()["data"] == []


def test_order_is_visible_to_member_and_shop_only(client: TestClient) -> None:
    buy_pass(client)
    order_id = order(client).json()["data"]["id"]
    stranger = bearer(make_access_token(KEYS.private_pem, uuid.uuid4()))

    assert client.get(f"{ORDERS}/{order_id}", headers=AUTH).status_code == 200
    assert client.get(f"{ORDERS}/{order_id}", headers=OWNER).status_code == 200
    assert client.get(f"{ORDERS}/{order_id}", headers=stranger).status_code == 404


def test_history_favorites_and_reorder(client: TestClient) -> None:
    buy_pass(client)
    first = order(client, size="L", milk="OAT").json()["data"]["id"]
    order(client)
    client.patch(f"{ORDERS}/{first}/favorite", headers=AUTH, json={"is_favorite": True})

    history = client.get(f"{ORDERS}/history", headers=AUTH).json()["data"]
    favorites = client.get(f"{ORDERS}/history?favorites=true", headers=AUTH).json()["data"]
    again = client.post(f"{ORDERS}/{first}/reorder", headers=AUTH).json()["data"]

    assert history["total"] == 2
    assert history["items"][0]["id"] != first  # newest first
    assert [o["id"] for o in favorites["items"]] == [first]
    assert (again["size"], again["milk"]) == ("L", "OAT")
    assert again["id"] != first
    assert credits(client) == 7

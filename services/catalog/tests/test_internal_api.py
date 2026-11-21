import uuid
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from brewpass_common.seed_ids import user_id
from catalog_service.api.shops import get_now
from catalog_service.seed import product_id, seed, shop_id
from tests.conftest import INTERNAL_TOKEN

HEADERS = {"X-Internal-Token": INTERNAL_TOKEN}


def test_internal_routes_require_the_internal_token(client: TestClient) -> None:
    response = client.get(f"/internal/shops/{uuid.uuid4()}")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INTERNAL_ONLY"


def test_get_product_includes_shop_and_owner(client: TestClient, db_session: Session) -> None:
    seed(db_session)

    response = client.get(
        f"/internal/products/{product_id('Moda Roastery', 'Flat White')}", headers=HEADERS
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["name"] == "Flat White"
    assert data["is_available"] is True
    assert data["shop"]["id"] == str(shop_id("Moda Roastery"))
    assert data["shop"]["owner_id"] == str(user_id("+905550000011"))


def test_unknown_product_returns_specific_error_code(client: TestClient) -> None:
    response = client.get(f"/internal/products/{uuid.uuid4()}", headers=HEADERS)

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "PRODUCT_NOT_FOUND"


def test_get_shop(client: TestClient, db_session: Session) -> None:
    seed(db_session)

    response = client.get(f"/internal/shops/{shop_id('Levent Daily Grind')}", headers=HEADERS)

    assert response.json()["data"]["name"] == "Levent Daily Grind"


def test_health_checks_database(client: TestClient) -> None:
    data = client.get("/health").json()["data"]

    assert data == {
        "service": "catalog",
        "status": "ok",
        "environment": "test",
        "database": "ok",
    }


@pytest.mark.parametrize(
    ("now", "expected"),
    [
        (datetime(2026, 11, 18, 7, 0, tzinfo=UTC), True),  # Wednesday 10:00 Istanbul
        (datetime(2026, 11, 22, 6, 30, tzinfo=UTC), False),  # Sunday 09:30, opens at 10:00
    ],
)
def test_product_lookup_reports_whether_shop_is_open(
    client: TestClient, db_session: Session, now: datetime, expected: bool
) -> None:
    seed(db_session)
    client.app.dependency_overrides[get_now] = lambda: now  # type: ignore[attr-defined]

    response = client.get(
        f"/internal/products/{product_id('Cihangir Corner Café', 'Espresso')}", headers=HEADERS
    )

    assert response.json()["data"]["shop"]["is_open_now"] is expected

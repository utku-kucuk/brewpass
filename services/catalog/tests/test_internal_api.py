import uuid

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from brewpass_common.seed_ids import user_id
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

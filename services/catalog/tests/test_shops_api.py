import uuid
from collections.abc import Iterator
from datetime import UTC, datetime

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from catalog_service.api.shops import get_now
from catalog_service.db import get_db
from catalog_service.main import create_app
from catalog_service.models import Product, Shop
from catalog_service.seed import product_id, seed, shop_id

SHOPS = "/api/v1/shops"
KARAKOY_PIER = {"lat": 41.0222, "lng": 28.9765}
# Wednesday 10:00 in Istanbul (UTC+3): every seeded shop is open.
WEDNESDAY_10AM = datetime(2026, 11, 18, 7, 0, tzinfo=UTC)
# Sunday 09:30 in Istanbul: only shops opening at 09:00 on weekends are open.
SUNDAY_0930 = datetime(2026, 11, 22, 6, 30, tzinfo=UTC)


def make_client(db_session: Session, now: datetime) -> TestClient:
    seed(db_session)
    app = create_app()
    app.dependency_overrides[get_db] = lambda: db_session
    app.dependency_overrides[get_now] = lambda: now
    return TestClient(app)


@pytest.fixture
def api(db_session: Session) -> Iterator[TestClient]:
    with make_client(db_session, WEDNESDAY_10AM) as client:
        yield client


def names(response: httpx.Response) -> list[str]:
    return [shop["name"] for shop in response.json()["data"]["items"]]


# --- Search --------------------------------------------------------------------------------


def test_without_location_lists_all_shops_by_rating(api: TestClient) -> None:
    data = api.get(SHOPS).json()["data"]

    ratings = [float(shop["rating"]) for shop in data["items"]]
    assert data["total"] == 6
    assert ratings == sorted(ratings, reverse=True)
    assert all(shop["distance_m"] is None for shop in data["items"])


def test_nearby_search_filters_by_radius_and_sorts_by_distance(api: TestClient) -> None:
    response = api.get(SHOPS, params={**KARAKOY_PIER, "radius": 2500})

    items = response.json()["data"]["items"]
    distances = [shop["distance_m"] for shop in items]
    assert names(response)[0] == "Karaköy Brew Lab"
    assert distances == sorted(distances)
    assert all(d <= 2500 for d in distances)
    assert "Levent Daily Grind" not in names(response)


def test_summary_contains_coordinates_and_today(api: TestClient) -> None:
    shop = api.get(SHOPS, params={**KARAKOY_PIER, "radius": 500}).json()["data"]["items"][0]

    assert shop["location"] == {"lat": pytest.approx(41.02445), "lng": pytest.approx(28.9772)}
    assert shop["today"] == {
        "weekday": 2,
        "day": "Wednesday",
        "opens_at": "07:30:00",
        "closes_at": "21:00:00",
    }
    assert shop["is_open_now"] is True


def test_text_search_matches_name_and_address(api: TestClient) -> None:
    assert names(api.get(SHOPS, params={"q": "roastery"})) == ["Moda Roastery"]
    assert names(api.get(SHOPS, params={"q": "Büyükdere"})) == ["Levent Daily Grind"]
    assert names(api.get(SHOPS, params={"q": "100%_"})) == []


def test_min_rating_filter(api: TestClient) -> None:
    response = api.get(SHOPS, params={"min_rating": "4.7"})

    assert set(names(response)) == {"Moda Roastery", "Nişantaşı Espresso Bar"}


def test_open_now_uses_local_opening_hours(db_session: Session) -> None:
    with make_client(db_session, SUNDAY_0930) as client:
        open_shops = set(names(client.get(SHOPS, params={"open_now": True})))
        all_shops = client.get(SHOPS).json()["data"]["items"]

    assert open_shops == {"Moda Roastery", "Karaköy Brew Lab", "Beşiktaş Bean House"}
    closed = {s["name"]: s["today"] for s in all_shops if not s["is_open_now"]}
    assert closed["Levent Daily Grind"]["opens_at"] is None  # closed on weekends
    assert closed["Cihangir Corner Café"]["opens_at"] == "10:00:00"


def test_pagination(api: TestClient) -> None:
    first = api.get(SHOPS, params={"sort": "name", "limit": 4}).json()["data"]
    second = api.get(SHOPS, params={"sort": "name", "limit": 4, "offset": 4}).json()["data"]

    assert (first["total"], len(first["items"]), len(second["items"])) == (6, 4, 2)
    assert not {s["id"] for s in first["items"]} & {s["id"] for s in second["items"]}


def test_inactive_shops_are_hidden(api: TestClient, db_session: Session) -> None:
    shop = db_session.get(Shop, shop_id("Moda Roastery"))
    assert shop is not None
    shop.is_active = False
    db_session.flush()

    assert "Moda Roastery" not in names(api.get(SHOPS))
    assert api.get(f"{SHOPS}/{shop.id}").status_code == 404


@pytest.mark.parametrize(
    "params",
    [
        {"lat": 41.0},
        {"lat": 91, "lng": 29},
        {"radius": 50, "lat": 41, "lng": 29},
        {"sort": "distance"},
        {"limit": 500},
    ],
    ids=["lat-only", "lat-range", "radius-too-small", "distance-without-location", "limit"],
)
def test_invalid_search_parameters(api: TestClient, params: dict) -> None:
    response = api.get(SHOPS, params=params)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


# --- Detail and menu -----------------------------------------------------------------------


def test_shop_detail_includes_week_and_distance(api: TestClient) -> None:
    response = api.get(f"{SHOPS}/{shop_id('Cihangir Corner Café')}", params=KARAKOY_PIER)

    data = response.json()["data"]
    assert data["name"] == "Cihangir Corner Café"
    assert data["description"]
    assert 500 < data["distance_m"] < 2000
    assert [d["day"] for d in data["opening_hours"]][0] == "Monday"
    assert data["opening_hours"][6]["opens_at"] == "10:00:00"


def test_unknown_shop_is_not_found(api: TestClient) -> None:
    response = api.get(f"{SHOPS}/{uuid.uuid4()}")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "SHOP_NOT_FOUND"


def test_menu_lists_products_with_availability(api: TestClient, db_session: Session) -> None:
    product = db_session.get(Product, product_id("Karaköy Brew Lab", "Cold Brew"))
    assert product is not None
    product.is_available = False
    db_session.flush()

    data = api.get(f"{SHOPS}/{shop_id('Karaköy Brew Lab')}/menu").json()["data"]

    assert data["shop_name"] == "Karaköy Brew Lab"
    assert len(data["items"]) == 5
    cold_brew = next(item for item in data["items"] if item["name"] == "Cold Brew")
    assert cold_brew["is_available"] is False
    assert cold_brew["category"] == "COLD_COFFEE"


def test_menu_of_unknown_shop_is_not_found(api: TestClient) -> None:
    assert api.get(f"{SHOPS}/{uuid.uuid4()}/menu").status_code == 404

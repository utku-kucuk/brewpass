from geoalchemy2 import WKTElement
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from brewpass_common.seed_ids import SHOP_OWNER_PHONES, user_id
from catalog_service.models import Product, Shop
from catalog_service.seed import SHOPS, seed


def test_seed_creates_minimum_data_and_is_idempotent(db_session: Session) -> None:
    seed(db_session)
    seed(db_session)

    assert db_session.scalar(select(func.count()).select_from(Shop)) == len(SHOPS) >= 5
    assert db_session.scalar(select(func.count()).select_from(Product)) >= 10


def test_shop_owners_match_accounts_seeded_by_auth_service(db_session: Session) -> None:
    seed(db_session)

    owner_ids = set(db_session.scalars(select(Shop.owner_id)))

    assert owner_ids == {user_id(phone) for phone in SHOP_OWNER_PHONES}


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

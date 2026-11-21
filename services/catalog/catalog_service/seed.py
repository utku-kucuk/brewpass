"""Idempotent seed data: Istanbul partner shops, opening hours and menus.

Shop owners are the accounts seeded by the auth service; their ids are derived from their phone
numbers (`brewpass_common.seed_ids`), so no cross-service lookup is needed.
Run with: `python -m catalog_service.seed`
"""

import uuid
from dataclasses import dataclass, field
from datetime import time
from decimal import Decimal

from geoalchemy2 import WKTElement
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from brewpass_common.seed_ids import seed_id, user_id
from catalog_service.db import SessionLocal
from catalog_service.models import Product, ProductCategory, Shop, ShopOpeningHours


@dataclass
class ShopSeed:
    name: str
    owner_phone: str
    address: str
    lat: float
    lng: float
    rating: str
    description: str
    weekday_hours: tuple[time, time] = (time(7, 30), time(21, 0))
    weekend_hours: tuple[time, time] | None = (time(9, 0), time(22, 0))
    menu: list[tuple[str, ProductCategory, str, str]] = field(default_factory=list)


STANDARD_MENU = [
    ("Espresso", ProductCategory.HOT_COFFEE, "65.00", "A short, intense double shot."),
    ("Flat White", ProductCategory.HOT_COFFEE, "95.00", "Double ristretto with silky milk."),
    ("Caffè Latte", ProductCategory.HOT_COFFEE, "90.00", "Espresso with steamed milk."),
    ("Iced Americano", ProductCategory.COLD_COFFEE, "85.00", "Espresso over ice and water."),
]

SHOPS = [
    ShopSeed(
        name="Moda Roastery",
        owner_phone="+905550000011",
        address="Moda Cd. No:42, Kadıköy",
        lat=40.98395,
        lng=29.02640,
        rating="4.7",
        description="Small-batch roastery a few steps from the Moda seaside.",
        menu=[
            *STANDARD_MENU,
            ("Filter Coffee", ProductCategory.HOT_COFFEE, "80.00", "Single-origin V60 of the day."),
        ],
    ),
    ShopSeed(
        name="Karaköy Brew Lab",
        owner_phone="+905550000012",
        address="Kemankeş Karamustafa Paşa Mah. No:18, Karaköy",
        lat=41.02445,
        lng=28.97720,
        rating="4.6",
        description="Specialty coffee bar with cold brew on tap.",
        menu=[
            *STANDARD_MENU,
            ("Cold Brew", ProductCategory.COLD_COFFEE, "95.00", "Steeped for 18 hours."),
        ],
    ),
    ShopSeed(
        name="Cihangir Corner Café",
        owner_phone="+905550000013",
        address="Akarsu Yokuşu No:7, Cihangir",
        lat=41.03130,
        lng=28.98330,
        rating="4.4",
        description="Neighbourhood café with a sunny corner terrace.",
        weekend_hours=(time(10, 0), time(23, 0)),
        menu=[
            *STANDARD_MENU,
            ("Turkish Coffee", ProductCategory.HOT_COFFEE, "70.00", "Served with lokum."),
            ("Earl Grey Tea", ProductCategory.TEA, "60.00", "Loose-leaf black tea."),
        ],
    ),
    ShopSeed(
        name="Beşiktaş Bean House",
        owner_phone="+905550000014",
        address="Sinanpaşa Mah. Ortabahçe Cd. No:21, Beşiktaş",
        lat=41.04300,
        lng=29.00560,
        rating="4.3",
        description="Busy espresso bar near the ferry pier.",
        weekday_hours=(time(7, 0), time(22, 0)),
        menu=[
            *STANDARD_MENU,
            ("Cappuccino", ProductCategory.HOT_COFFEE, "88.00", "Equal parts espresso and foam."),
        ],
    ),
    ShopSeed(
        name="Nişantaşı Espresso Bar",
        owner_phone="+905550000015",
        address="Teşvikiye Mah. Abdi İpekçi Cd. No:33, Şişli",
        lat=41.05090,
        lng=28.99390,
        rating="4.8",
        description="Standing espresso bar in the heart of Nişantaşı.",
        weekend_hours=None,
        menu=[
            *STANDARD_MENU,
            ("Cortado", ProductCategory.HOT_COFFEE, "80.00", "Espresso cut with warm milk."),
        ],
    ),
    ShopSeed(
        name="Levent Daily Grind",
        owner_phone="+905550000016",
        address="Levent Mah. Büyükdere Cd. No:185, Beşiktaş",
        lat=41.08130,
        lng=29.01090,
        rating="4.2",
        description="Grab-and-go coffee for the business district.",
        weekday_hours=(time(6, 30), time(20, 0)),
        weekend_hours=None,
        menu=[
            *STANDARD_MENU,
            ("Matcha Latte", ProductCategory.OTHER, "105.00", "Ceremonial-grade matcha."),
        ],
    ),
]


def shop_id(name: str) -> uuid.UUID:
    return seed_id("shop", name)


def product_id(shop_name: str, product_name: str) -> uuid.UUID:
    return seed_id("product", f"{shop_name}:{product_name}")


def seed_shops(session: Session) -> None:
    for data in SHOPS:
        shop = session.get(Shop, shop_id(data.name))
        if shop is None:
            shop = Shop(id=shop_id(data.name), name=data.name)
            session.add(shop)
        shop.owner_id = user_id(data.owner_phone)
        shop.address = data.address
        shop.city = "Istanbul"
        shop.description = data.description
        shop.rating = Decimal(data.rating)
        shop.location = WKTElement(f"POINT({data.lng} {data.lat})", srid=4326)

        shop.opening_hours.clear()
        session.flush()
        for weekday in range(7):
            hours = data.weekday_hours if weekday < 5 else data.weekend_hours
            if hours is not None:
                shop.opening_hours.append(
                    ShopOpeningHours(weekday=weekday, opens_at=hours[0], closes_at=hours[1])
                )
        session.flush()

        for name, category, price, description in data.menu:
            product = session.get(Product, product_id(data.name, name))
            if product is None:
                product = Product(id=product_id(data.name, name), shop_id=shop.id, name=name)
                session.add(product)
            product.category = category
            product.list_price = Decimal(price)
            product.description = description
            product.supports_milk = category != ProductCategory.TEA
            product.supports_extra_shot = category in (
                ProductCategory.HOT_COFFEE,
                ProductCategory.COLD_COFFEE,
            )


def seed(session: Session) -> None:
    seed_shops(session)
    session.commit()


def main() -> None:
    with SessionLocal() as session:
        seed(session)
        shops = session.scalar(select(func.count()).select_from(Shop))
        products = session.scalar(select(func.count()).select_from(Product))
    print(f"Catalog seed complete: shops={shops}, products={products}")


if __name__ == "__main__":
    main()

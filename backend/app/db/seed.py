"""Idempotent seed data: subscription plans, demo users, Istanbul partner shops and menus.

Run with: `python -m app.db.seed`
"""

from dataclasses import dataclass, field
from datetime import time
from decimal import Decimal

from geoalchemy2 import WKTElement
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models import Plan, Product, Shop, ShopOpeningHours, User
from app.models.enums import PlanCode, ProductCategory, UserRole

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

DEMO_USERS = [
    {"phone_number": "+905550000001", "full_name": "BrewPass Admin", "role": UserRole.ADMIN},
    {
        "phone_number": "+905550000100",
        "full_name": "Demo Customer",
        "email": "demo@brewpass.app",
        "role": UserRole.CUSTOMER,
        "preferences": {"favorite_drinks": ["Flat White"], "allergens": []},
    },
]


@dataclass
class ShopSeed:
    name: str
    owner_phone: str
    owner_name: str
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
        owner_name="Deniz Aydın",
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
        owner_name="Ece Yılmaz",
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
        owner_name="Mert Kaya",
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
        owner_name="Selin Demir",
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
        owner_name="Can Öztürk",
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
        owner_name="Ayşe Şahin",
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


def _upsert_user(session: Session, phone_number: str, **values: object) -> User:
    user = session.scalar(select(User).where(User.phone_number == phone_number))
    if user is None:
        user = User(phone_number=phone_number)
        session.add(user)
    for key, value in values.items():
        setattr(user, key, value)
    return user


def seed_plans(session: Session) -> None:
    for data in PLANS:
        plan = session.scalar(select(Plan).where(Plan.code == data["code"]))
        if plan is None:
            plan = Plan(code=data["code"])
            session.add(plan)
        for key, value in data.items():
            setattr(plan, key, value)


def seed_users(session: Session) -> None:
    for data in DEMO_USERS:
        _upsert_user(session, **data)


def seed_shops(session: Session) -> None:
    for data in SHOPS:
        owner = _upsert_user(
            session, data.owner_phone, full_name=data.owner_name, role=UserRole.SHOP_OWNER
        )
        session.flush()

        shop = session.scalar(select(Shop).where(Shop.name == data.name))
        if shop is None:
            shop = Shop(name=data.name)
            session.add(shop)
        shop.owner_id = owner.id
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

        existing = {
            p.name: p for p in session.scalars(select(Product).where(Product.shop_id == shop.id))
        }
        for name, category, price, description in data.menu:
            product = existing.get(name) or Product(shop_id=shop.id, name=name)
            product.category = category
            product.list_price = Decimal(price)
            product.description = description
            product.supports_milk = category != ProductCategory.TEA
            product.supports_extra_shot = category in (
                ProductCategory.HOT_COFFEE,
                ProductCategory.COLD_COFFEE,
            )
            session.add(product)


def seed(session: Session) -> None:
    seed_plans(session)
    seed_users(session)
    seed_shops(session)
    session.commit()


def main() -> None:
    with SessionLocal() as session:
        seed(session)
        counts = {
            "plans": len(session.scalars(select(Plan)).all()),
            "shops": len(session.scalars(select(Shop)).all()),
            "products": len(session.scalars(select(Product)).all()),
            "users": len(session.scalars(select(User)).all()),
        }
    print("Seed complete:", ", ".join(f"{k}={v}" for k, v in counts.items()))


if __name__ == "__main__":
    main()

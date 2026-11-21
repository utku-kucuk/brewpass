"""Idempotent seed: admin, demo customer and one owner account per partner shop.

IDs are deterministic (`brewpass_common.seed_ids`) so the catalog service can assign shops to
these owners without reading this database. Run with: `python -m auth_service.seed`
"""

from sqlalchemy.orm import Session

from auth_service.db import SessionLocal
from auth_service.models import User
from brewpass_common.security import UserRole
from brewpass_common.seed_ids import (
    ADMIN_PHONE,
    DEMO_CUSTOMER_PHONE,
    SHOP_OWNER_PHONES,
    user_id,
)

SHOP_OWNER_NAMES = [
    "Deniz Aydın",
    "Ece Yılmaz",
    "Mert Kaya",
    "Selin Demir",
    "Can Öztürk",
    "Ayşe Şahin",
]

USERS = [
    {"phone_number": ADMIN_PHONE, "full_name": "BrewPass Admin", "role": UserRole.ADMIN},
    {
        "phone_number": DEMO_CUSTOMER_PHONE,
        "full_name": "Demo Customer",
        "email": "demo@brewpass.app",
        "role": UserRole.CUSTOMER,
        "preferences": {"favorite_drinks": ["Flat White"], "allergens": []},
    },
    *(
        {"phone_number": phone, "full_name": name, "role": UserRole.SHOP_OWNER}
        for phone, name in zip(SHOP_OWNER_PHONES, SHOP_OWNER_NAMES, strict=True)
    ),
]


def seed(session: Session) -> int:
    for data in USERS:
        data = dict(data)
        phone = data.pop("phone_number")
        user = session.get(User, user_id(phone))
        if user is None:
            user = User(id=user_id(phone), phone_number=phone, preferences={})
            session.add(user)
        for key, value in data.items():
            setattr(user, key, value)
    session.commit()
    return len(USERS)


def main() -> None:
    with SessionLocal() as session:
        count = seed(session)
    print(f"Auth seed complete: users={count}")


if __name__ == "__main__":
    main()

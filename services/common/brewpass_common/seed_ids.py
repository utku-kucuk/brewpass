"""Deterministic IDs for seed data, so records created by different services line up.

Example: the catalog service assigns a shop to the owner the auth service seeded, without either
service reading the other's database.
"""

import uuid

_NAMESPACE = uuid.uuid5(uuid.NAMESPACE_URL, "https://brewpass.app/seed")


def seed_id(kind: str, key: str) -> uuid.UUID:
    return uuid.uuid5(_NAMESPACE, f"{kind}:{key}")


def user_id(phone_number: str) -> uuid.UUID:
    return seed_id("user", phone_number)


# Phone numbers of the seeded accounts (see services/auth seed).
ADMIN_PHONE = "+905550000001"
DEMO_CUSTOMER_PHONE = "+905550000100"
SHOP_OWNER_PHONES = [f"+9055500000{n}" for n in range(11, 17)]

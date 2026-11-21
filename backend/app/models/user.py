from typing import Any

from sqlalchemy import Enum, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import UserRole


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "users"

    # E.164 format, e.g. +905551234567
    phone_number: Mapped[str] = mapped_column(String(15), unique=True, index=True)
    # Filled in on the profile completion step after the first sign-in.
    full_name: Mapped[str | None] = mapped_column(String(100))
    email: Mapped[str | None] = mapped_column(String(255))
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role"), default=UserRole.CUSTOMER
    )
    # Favourite drinks and allergens, e.g. {"favorite_drinks": [...], "allergens": [...]}
    preferences: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, server_default="{}")

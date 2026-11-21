import uuid
from datetime import time
from decimal import Decimal

from geoalchemy2 import Geography, WKBElement
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    Numeric,
    SmallInteger,
    String,
    Text,
    Time,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Shop(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "shops"
    __table_args__ = (CheckConstraint("rating >= 0 AND rating <= 5", name="rating_range"),)

    owner_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    name: Mapped[str] = mapped_column(String(120))
    description: Mapped[str | None] = mapped_column(Text)
    address: Mapped[str] = mapped_column(String(255))
    city: Mapped[str] = mapped_column(String(60), index=True)
    phone_number: Mapped[str | None] = mapped_column(String(15))
    # WGS 84 point; a GiST index is created for radius queries.
    location: Mapped[WKBElement] = mapped_column(
        Geography(geometry_type="POINT", srid=4326, spatial_index=True)
    )
    rating: Mapped[Decimal] = mapped_column(Numeric(2, 1), default=Decimal("0.0"))
    photo_url: Mapped[str | None] = mapped_column(String(500))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    opening_hours: Mapped[list["ShopOpeningHours"]] = relationship(
        back_populates="shop", cascade="all, delete-orphan", order_by="ShopOpeningHours.weekday"
    )


class ShopOpeningHours(UUIDPrimaryKeyMixin, Base):
    """Opening hours per weekday (0 = Monday ... 6 = Sunday). A missing day means closed."""

    __tablename__ = "shop_opening_hours"
    __table_args__ = (
        UniqueConstraint("shop_id", "weekday", name="uq_shop_opening_hours_shop_id_weekday"),
        CheckConstraint("weekday BETWEEN 0 AND 6", name="weekday_range"),
        CheckConstraint("closes_at > opens_at", name="hours_valid"),
    )

    shop_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("shops.id", ondelete="CASCADE"))
    weekday: Mapped[int] = mapped_column(SmallInteger)
    opens_at: Mapped[time] = mapped_column(Time)
    closes_at: Mapped[time] = mapped_column(Time)

    shop: Mapped[Shop] = relationship(back_populates="opening_hours")

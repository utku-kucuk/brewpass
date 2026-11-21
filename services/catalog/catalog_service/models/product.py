import enum
import uuid
from decimal import Decimal

from sqlalchemy import Boolean, CheckConstraint, Enum, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from brewpass_common.db import TimestampMixin, UUIDPrimaryKeyMixin
from catalog_service.db import Base
from catalog_service.models.shop import Shop


class ProductCategory(enum.StrEnum):
    HOT_COFFEE = "HOT_COFFEE"
    COLD_COFFEE = "COLD_COFFEE"
    TEA = "TEA"
    OTHER = "OTHER"


class Product(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A drink on a shop's menu. Members redeem one credit per drink."""

    __tablename__ = "products"
    __table_args__ = (CheckConstraint("list_price >= 0", name="list_price_non_negative"),)

    shop_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("shops.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(100))
    description: Mapped[str | None] = mapped_column(Text)
    category: Mapped[ProductCategory] = mapped_column(
        Enum(ProductCategory, name="product_category")
    )
    # Over-the-counter price, shown to illustrate the value of a credit.
    list_price: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    supports_milk: Mapped[bool] = mapped_column(Boolean, default=True)
    supports_extra_shot: Mapped[bool] = mapped_column(Boolean, default=True)
    image_url: Mapped[str | None] = mapped_column(String(500))
    is_available: Mapped[bool] = mapped_column(Boolean, default=True)

    shop: Mapped[Shop] = relationship()

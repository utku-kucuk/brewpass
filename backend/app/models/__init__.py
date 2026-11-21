"""SQLAlchemy models. Importing this package registers every table on `Base.metadata`."""

from app.models.auth import OtpChallenge, RefreshToken
from app.models.base import Base
from app.models.order import Order, OrderStatusEvent
from app.models.payment import Payment
from app.models.plan import Plan
from app.models.product import Product
from app.models.shop import Shop, ShopOpeningHours
from app.models.subscription import Subscription
from app.models.user import User

__all__ = [
    "Base",
    "Order",
    "OrderStatusEvent",
    "OtpChallenge",
    "Payment",
    "Plan",
    "Product",
    "RefreshToken",
    "Shop",
    "ShopOpeningHours",
    "Subscription",
    "User",
]

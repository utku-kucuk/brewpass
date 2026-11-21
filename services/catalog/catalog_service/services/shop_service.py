import uuid
from datetime import datetime, time
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from brewpass_common.errors import NotFoundError
from catalog_service.config import get_settings
from catalog_service.models import Shop
from catalog_service.repositories.shop_repository import ShopRepository, ShopRow
from catalog_service.schemas.shop import (
    WEEKDAYS,
    Coordinates,
    DayHours,
    MenuItemOut,
    MenuOut,
    ShopDetailOut,
    ShopPage,
    ShopSearchParams,
    ShopSummaryOut,
)


def week_hours(shop: Shop) -> list[DayHours]:
    by_day = {hours.weekday: hours for hours in shop.opening_hours}
    return [
        DayHours(
            weekday=day,
            day=WEEKDAYS[day],
            opens_at=by_day[day].opens_at if day in by_day else None,
            closes_at=by_day[day].closes_at if day in by_day else None,
        )
        for day in range(7)
    ]


def local_clock(now: datetime) -> tuple[int, time]:
    """Weekday and wall-clock time in the shops' time zone (opening hours are local)."""
    local = now.astimezone(ZoneInfo(get_settings().shop_timezone))
    return local.weekday(), local.time().replace(tzinfo=None)


class ShopService:
    def __init__(self, session: Session, now: datetime) -> None:
        self.shops = ShopRepository(session)
        self.weekday, self.local_time = local_clock(now)

    def _summary_fields(self, row: ShopRow) -> dict:
        hours = week_hours(row.shop)
        return {
            "id": row.shop.id,
            "name": row.shop.name,
            "address": row.shop.address,
            "city": row.shop.city,
            "location": Coordinates(lat=row.lat, lng=row.lng),
            "rating": row.shop.rating,
            "photo_url": row.shop.photo_url,
            "distance_m": round(row.distance_m) if row.distance_m is not None else None,
            "is_open_now": row.is_open_now,
            "today": hours[self.weekday],
        }

    def search(self, params: ShopSearchParams) -> ShopPage:
        rows, total = self.shops.search(params, self.weekday, self.local_time)
        return ShopPage(
            items=[ShopSummaryOut(**self._summary_fields(row)) for row in rows],
            total=total,
            limit=params.limit,
            offset=params.offset,
        )

    def detail(
        self, shop_id: uuid.UUID, lat: float | None = None, lng: float | None = None
    ) -> ShopDetailOut:
        row = self.shops.get(shop_id, self.weekday, self.local_time, lat, lng)
        if row is None:
            raise NotFoundError("Shop not found.", code="SHOP_NOT_FOUND")
        return ShopDetailOut(
            **self._summary_fields(row),
            description=row.shop.description,
            phone_number=row.shop.phone_number,
            opening_hours=week_hours(row.shop),
        )

    def menu(self, shop_id: uuid.UUID) -> MenuOut:
        shop = self.shops.exists_active(shop_id)
        if shop is None:
            raise NotFoundError("Shop not found.", code="SHOP_NOT_FOUND")
        return MenuOut(
            shop_id=shop.id,
            shop_name=shop.name,
            items=[
                MenuItemOut(
                    id=product.id,
                    name=product.name,
                    description=product.description,
                    category=product.category,
                    list_price=product.list_price,
                    supports_milk=product.supports_milk,
                    supports_extra_shot=product.supports_extra_shot,
                    image_url=product.image_url,
                    is_available=product.is_available,
                )
                for product in self.shops.menu(shop.id)
            ],
        )

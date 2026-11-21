import uuid
from datetime import time
from decimal import Decimal
from enum import StrEnum
from typing import Annotated, Self

from fastapi import Query
from pydantic import BaseModel, Field, model_validator

from catalog_service.models import ProductCategory

WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


class ShopSort(StrEnum):
    DISTANCE = "distance"
    RATING = "rating"
    NAME = "name"


class ShopSearchParams(BaseModel):
    """Query parameters for `GET /shops`. Distance features need both `lat` and `lng`."""

    lat: float | None = Field(default=None, ge=-90, le=90)
    lng: float | None = Field(default=None, ge=-180, le=180)
    radius: int = Field(default=3000, ge=100, le=20000, description="Meters, used with lat/lng.")
    q: str | None = Field(default=None, min_length=1, max_length=60, description="Name or address.")
    min_rating: Decimal | None = Field(default=None, ge=0, le=5)
    open_now: bool = False
    sort: ShopSort | None = Field(
        default=None, description="Defaults to distance when a location is given, else rating."
    )
    limit: int = Field(default=20, ge=1, le=50)
    offset: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def _location_pair(self) -> Self:
        if (self.lat is None) != (self.lng is None):
            raise ValueError("Provide both lat and lng.")
        if self.sort == ShopSort.DISTANCE and self.lat is None:
            raise ValueError("Sorting by distance needs lat and lng.")
        return self

    @property
    def has_location(self) -> bool:
        return self.lat is not None and self.lng is not None

    @property
    def effective_sort(self) -> ShopSort:
        if self.sort is not None:
            return self.sort
        return ShopSort.DISTANCE if self.has_location else ShopSort.RATING


# FastAPI reads the model's fields from the query string.
ShopSearchQuery = Annotated[ShopSearchParams, Query()]


class Coordinates(BaseModel):
    lat: float
    lng: float


class DayHours(BaseModel):
    weekday: int = Field(description="0 = Monday … 6 = Sunday")
    day: str
    opens_at: time | None = Field(description="null when closed all day")
    closes_at: time | None


class ShopSummaryOut(BaseModel):
    id: uuid.UUID
    name: str
    address: str
    city: str
    location: Coordinates
    rating: Decimal
    photo_url: str | None
    distance_m: int | None = Field(description="Meters from the given location, if any.")
    is_open_now: bool
    today: DayHours


class ShopDetailOut(ShopSummaryOut):
    description: str | None
    phone_number: str | None
    opening_hours: list[DayHours]


class ShopPage(BaseModel):
    items: list[ShopSummaryOut]
    total: int
    limit: int
    offset: int


class MenuItemOut(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None
    category: ProductCategory
    list_price: Decimal = Field(description="Over-the-counter price; members pay with a credit.")
    supports_milk: bool
    supports_extra_shot: bool
    image_url: str | None
    is_available: bool


class MenuOut(BaseModel):
    shop_id: uuid.UUID
    shop_name: str
    items: list[MenuItemOut]

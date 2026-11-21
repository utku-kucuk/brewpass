"""Shop queries. Distance and radius filtering run in PostGIS on the geography column (GiST)."""

import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import time

from geoalchemy2 import Geometry, WKTElement
from sqlalchemy import ColumnElement, Row, Select, and_, case, cast, exists, func, or_, select
from sqlalchemy.orm import Session, selectinload

from catalog_service.models import Product, Shop, ShopOpeningHours
from catalog_service.schemas.shop import ShopSearchParams, ShopSort


@dataclass(frozen=True)
class ShopRow:
    shop: Shop
    lat: float
    lng: float
    distance_m: float | None
    is_open_now: bool


def _point(lat: float, lng: float) -> WKTElement:
    return WKTElement(f"POINT({lng} {lat})", srid=4326)


def _escape_like(term: str) -> str:
    return term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def open_at(weekday: int, local_time: time) -> ColumnElement[bool]:
    return exists().where(
        ShopOpeningHours.shop_id == Shop.id,
        ShopOpeningHours.weekday == weekday,
        ShopOpeningHours.opens_at <= local_time,
        ShopOpeningHours.closes_at > local_time,
    )


class ShopRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def _base(
        self, weekday: int, local_time: time, lat: float | None, lng: float | None
    ) -> tuple[Select, ColumnElement | None, ColumnElement[bool]]:
        """Active shops with coordinates, open-now flag and (given a location) distance."""
        geometry = cast(Shop.location, Geometry)
        is_open = open_at(weekday, local_time)
        distance = (
            func.ST_Distance(Shop.location, _point(lat, lng))
            if lat is not None and lng is not None
            else None
        )
        select_columns = [
            Shop,
            func.ST_Y(geometry).label("lat"),
            func.ST_X(geometry).label("lng"),
            case((is_open, True), else_=False).label("is_open_now"),
        ]
        if distance is not None:
            select_columns.append(distance.label("distance_m"))
        base = (
            select(*select_columns)
            .where(Shop.is_active.is_(True))
            .options(selectinload(Shop.opening_hours))
        )
        return base, distance, is_open

    def search(
        self, params: ShopSearchParams, weekday: int, local_time: time
    ) -> tuple[Sequence[ShopRow], int]:
        query, distance, is_open = self._base(weekday, local_time, params.lat, params.lng)

        if distance is not None:
            assert params.lat is not None and params.lng is not None
            query = query.where(
                func.ST_DWithin(Shop.location, _point(params.lat, params.lng), params.radius)
            )
        if params.q:
            pattern = f"%{_escape_like(params.q)}%"
            query = query.where(
                or_(Shop.name.ilike(pattern, escape="\\"), Shop.address.ilike(pattern, escape="\\"))
            )
        if params.min_rating is not None:
            query = query.where(Shop.rating >= params.min_rating)
        if params.open_now:
            query = query.where(is_open)

        total = self.session.scalar(
            select(func.count()).select_from(query.with_only_columns(Shop.id).subquery())
        )

        sort = params.effective_sort
        if sort == ShopSort.DISTANCE and distance is not None:
            query = query.order_by(distance, Shop.name)
        elif sort == ShopSort.NAME:
            query = query.order_by(Shop.name)
        else:
            query = query.order_by(Shop.rating.desc(), Shop.name)

        rows = self.session.execute(query.limit(params.limit).offset(params.offset)).all()
        return [self._row(row) for row in rows], int(total or 0)

    def get(
        self,
        shop_id: uuid.UUID,
        weekday: int,
        local_time: time,
        lat: float | None = None,
        lng: float | None = None,
    ) -> ShopRow | None:
        query, _, _ = self._base(weekday, local_time, lat, lng)
        row = self.session.execute(query.where(Shop.id == shop_id)).first()
        return self._row(row) if row else None

    @staticmethod
    def _row(row: Row) -> ShopRow:
        mapping = row._mapping
        distance = mapping.get("distance_m")
        return ShopRow(
            shop=mapping[Shop],
            lat=float(mapping["lat"]),
            lng=float(mapping["lng"]),
            distance_m=float(distance) if distance is not None else None,
            is_open_now=bool(mapping["is_open_now"]),
        )

    def menu(self, shop_id: uuid.UUID) -> Sequence[Product]:
        return self.session.scalars(
            select(Product)
            .where(Product.shop_id == shop_id)
            .order_by(Product.category, Product.name)
        ).all()

    def exists_active(self, shop_id: uuid.UUID) -> Shop | None:
        return self.session.scalar(
            select(Shop).where(and_(Shop.id == shop_id, Shop.is_active.is_(True)))
        )

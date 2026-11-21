import uuid
from collections.abc import Sequence

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session, selectinload

from commerce_service.models import Order, OrderStatus

ACTIVE_STATUSES = (
    OrderStatus.PENDING,
    OrderStatus.ACCEPTED,
    OrderStatus.PREPARING,
    OrderStatus.READY,
)


class OrderRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, order_id: uuid.UUID, *, lock: bool = False) -> Order | None:
        query = select(Order).where(Order.id == order_id).options(selectinload(Order.status_events))
        if lock:
            query = query.with_for_update(of=Order)
        return self.session.scalar(query)

    def history(
        self, user_id: uuid.UUID, *, favorites_only: bool, limit: int, offset: int
    ) -> tuple[Sequence[Order], int]:
        query = select(Order).where(Order.user_id == user_id)
        if favorites_only:
            query = query.where(Order.is_favorite.is_(True))
        total = self.session.scalar(select(func.count()).select_from(query.subquery()))
        orders = self.session.scalars(
            query.options(selectinload(Order.status_events))
            .order_by(Order.created_at.desc(), Order.id.desc())
            .limit(limit)
            .offset(offset)
        ).all()
        return orders, int(total or 0)

    def incoming_for_owner(self, owner_id: uuid.UUID) -> Sequence[Order]:
        """Open orders across the owner's shops: priority first, then oldest first."""
        return self.session.scalars(
            select(Order)
            .where(Order.shop_owner_id == owner_id, Order.status.in_(ACTIVE_STATUSES))
            .options(selectinload(Order.status_events))
            .order_by(
                case((Order.is_priority.is_(True), 0), else_=1),
                Order.created_at,
            )
        ).all()

"""Database helpers shared by services. Each service declares its own `Base` (own metadata)."""

import uuid
from collections.abc import Callable, Iterator
from datetime import UTC, datetime

from sqlalchemy import DateTime, MetaData, create_engine, func
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

# Deterministic constraint names keep Alembic migrations stable and readable.
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


def new_metadata() -> MetaData:
    return MetaData(naming_convention=NAMING_CONVENTION)


class SessionFactory:
    """Lazily creates the engine so importing a service never opens a connection."""

    def __init__(self, url_getter: Callable[[], str]) -> None:
        self._url_getter = url_getter
        self._sessionmaker: sessionmaker[Session] | None = None

    def __call__(self) -> Session:
        if self._sessionmaker is None:
            engine = create_engine(self._url_getter(), pool_pre_ping=True)
            self._sessionmaker = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
        return self._sessionmaker()

    def get_db(self) -> Iterator[Session]:
        """FastAPI dependency yielding one session per request."""
        with self() as session:
            yield session


__all__ = ["DeclarativeBase", "SessionFactory", "TimestampMixin", "UUIDPrimaryKeyMixin"]


class UUIDPrimaryKeyMixin:
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)


def _utcnow() -> datetime:
    return datetime.now(UTC)


class TimestampMixin:
    # Set in Python so rows created in one transaction still get distinct, ordered timestamps
    # (SQL `now()` is the transaction start time). The server default covers raw SQL inserts.
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utcnow,
        onupdate=_utcnow,
        server_default=func.now(),
        nullable=False,
    )

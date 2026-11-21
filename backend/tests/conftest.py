"""Shared test fixtures.

Tests run against a real PostgreSQL + PostGIS database (`brewpass_test` by default). The database
is recreated and migrated once per test session; every test runs inside a transaction that is
rolled back afterwards.
"""

import os
from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

BACKEND_DIR = Path(__file__).resolve().parent.parent
TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+psycopg://brewpass:brewpass@localhost:5432/brewpass_test",
)


def _recreate_database(url: str) -> None:
    db_url = make_url(url)
    admin_engine = create_engine(db_url.set(database="postgres"), isolation_level="AUTOCOMMIT")
    with admin_engine.connect() as conn:
        conn.execute(text(f'DROP DATABASE IF EXISTS "{db_url.database}" WITH (FORCE)'))
        conn.execute(text(f'CREATE DATABASE "{db_url.database}"'))
    admin_engine.dispose()


def _run_migrations(url: str) -> None:
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    config.set_main_option("sqlalchemy.url", url)
    command.upgrade(config, "head")


@pytest.fixture(scope="session")
def engine() -> Iterator[Engine]:
    _recreate_database(TEST_DATABASE_URL)
    _run_migrations(TEST_DATABASE_URL)
    engine = create_engine(TEST_DATABASE_URL)
    yield engine
    engine.dispose()


@pytest.fixture
def db_session(engine: Engine) -> Iterator[Session]:
    """A session whose changes (including commits) are rolled back after the test."""
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(
        bind=connection, join_transaction_mode="create_savepoint", expire_on_commit=False
    )
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()

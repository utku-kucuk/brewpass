"""Auth service test fixtures.

Tests run against a real PostgreSQL database (`brewpass_auth_test`), recreated and migrated once
per session. Each test runs in a transaction that is rolled back afterwards.
"""

import os
from collections.abc import Iterator
from pathlib import Path

from brewpass_common.testing import generate_key_pair, prepared_engine, rollback_session

# Must be set before the service settings are created.
_KEYS = generate_key_pair()
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("RATE_LIMIT_ENABLED", "false")
os.environ.setdefault("LOG_FORMAT", "text")
os.environ.setdefault("LOG_LEVEL", "WARNING")
os.environ["JWT_PRIVATE_KEY"] = _KEYS.private_pem
os.environ["JWT_PUBLIC_KEY"] = _KEYS.public_pem

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import Engine  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from auth_service.db import get_db  # noqa: E402
from auth_service.main import create_app  # noqa: E402

SERVICE_DIR = Path(__file__).resolve().parent.parent
TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+psycopg://brewpass:brewpass@localhost:5432/brewpass_auth_test",
)


@pytest.fixture(scope="session")
def engine() -> Iterator[Engine]:
    engine = prepared_engine(SERVICE_DIR, TEST_DATABASE_URL)
    yield engine
    engine.dispose()


@pytest.fixture
def db_session(engine: Engine) -> Iterator[Session]:
    yield from rollback_session(engine)


@pytest.fixture
def client(db_session: Session) -> Iterator[TestClient]:
    """API client whose requests share the test's rolled-back database session."""
    app = create_app()
    app.dependency_overrides[get_db] = lambda: db_session
    with TestClient(app) as test_client:
        yield test_client

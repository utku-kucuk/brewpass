"""Commerce service test fixtures.

Tests run against a real PostgreSQL database (`brewpass_commerce_test`), recreated and migrated once
per session. Each test runs in a transaction that is rolled back afterwards. The payment service
is replaced by `FakePayments` (see `tests/fakes.py`).
"""

import os
from collections.abc import Iterator
from pathlib import Path

from brewpass_common.testing import generate_key_pair, prepared_engine, rollback_session

INTERNAL_TOKEN = "test-internal-token"
KEYS = generate_key_pair()

# Must be set before the service settings are created.
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("RATE_LIMIT_ENABLED", "false")
os.environ.setdefault("LOG_FORMAT", "text")
os.environ.setdefault("LOG_LEVEL", "WARNING")
os.environ.setdefault("INTERNAL_TOKEN", INTERNAL_TOKEN)
os.environ["JWT_PUBLIC_KEY"] = KEYS.public_pem

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import Engine  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from commerce_service.clients.catalog_client import get_catalog_client  # noqa: E402
from commerce_service.clients.payment_client import get_payment_client  # noqa: E402
from commerce_service.db import get_db  # noqa: E402
from commerce_service.main import create_app  # noqa: E402
from commerce_service.seed import seed  # noqa: E402
from tests.fakes import FakeCatalog, FakePayments  # noqa: E402

SERVICE_DIR = Path(__file__).resolve().parent.parent
TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+psycopg://brewpass:brewpass@localhost:5432/brewpass_commerce_test",
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
def payments() -> FakePayments:
    return FakePayments()


@pytest.fixture
def catalog() -> FakeCatalog:
    return FakeCatalog()


@pytest.fixture
def client(
    db_session: Session, payments: FakePayments, catalog: FakeCatalog
) -> Iterator[TestClient]:
    """API client sharing the test's rolled-back session, with plans seeded."""
    seed(db_session)
    app = create_app()
    app.dependency_overrides[get_db] = lambda: db_session
    app.dependency_overrides[get_payment_client] = lambda: payments
    app.dependency_overrides[get_catalog_client] = lambda: catalog
    with TestClient(app) as test_client:
        yield test_client

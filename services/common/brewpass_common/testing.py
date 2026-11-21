"""Test helpers shared by service test suites."""

from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

from alembic import command
from alembic.config import Config
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session


@dataclass(frozen=True)
class KeyPair:
    private_pem: str
    public_pem: str


def generate_key_pair() -> KeyPair:
    """A throwaway RSA key pair for signing test tokens."""
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    ).decode()
    public_pem = (
        key.public_key()
        .public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)
        .decode()
    )
    return KeyPair(private_pem=private_pem, public_pem=public_pem)


def recreate_database(url: str) -> None:
    db_url = make_url(url)
    admin_engine = create_engine(db_url.set(database="postgres"), isolation_level="AUTOCOMMIT")
    with admin_engine.connect() as conn:
        conn.execute(text(f'DROP DATABASE IF EXISTS "{db_url.database}" WITH (FORCE)'))
        conn.execute(text(f'CREATE DATABASE "{db_url.database}"'))
    admin_engine.dispose()


def migrate(service_dir: Path, url: str) -> None:
    config = Config(str(service_dir / "alembic.ini"))
    config.set_main_option("script_location", str(service_dir / "alembic"))
    config.set_main_option("sqlalchemy.url", url)
    command.upgrade(config, "head")


def prepared_engine(service_dir: Path, url: str) -> Engine:
    """Fresh, fully migrated test database."""
    recreate_database(url)
    migrate(service_dir, url)
    return create_engine(url)


def rollback_session(engine: Engine) -> Iterator[Session]:
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

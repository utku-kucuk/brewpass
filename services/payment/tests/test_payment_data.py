import uuid
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from payment_service.models import Payment, PaymentStatus


def _payment(**overrides: object) -> Payment:
    values: dict[str, object] = {
        "user_id": uuid.uuid4(),
        "description": "subscription:DAILY",
        "amount": Decimal("149.99"),
        "currency": "TRY",
        "status": PaymentStatus.SUCCEEDED,
        "card_last4": "4242",
        **overrides,
    }
    return Payment(**values)


def test_payment_gets_unique_transaction_id(db_session: Session) -> None:
    first, second = _payment(), _payment()
    db_session.add_all([first, second])
    db_session.flush()

    assert first.transaction_id != second.transaction_id


def test_negative_amount_is_rejected(db_session: Session) -> None:
    db_session.add(_payment(amount=Decimal("-1.00")))

    with pytest.raises(IntegrityError):
        db_session.flush()


def test_health_checks_database(client: TestClient) -> None:
    assert client.get("/health").json()["data"]["service"] == "payment"

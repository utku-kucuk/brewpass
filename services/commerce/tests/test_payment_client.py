import uuid
from decimal import Decimal

import httpx
import pytest
import respx

from brewpass_common.errors import AppError, ServiceUnavailableError
from brewpass_common.internal_client import InternalClient
from commerce_service.clients.payment_client import PaymentClient

BASE = "http://payment:8000"
URL = f"{BASE}/internal/payments/charge"


@pytest.fixture
def client() -> PaymentClient:
    return PaymentClient(InternalClient(BASE, "token"))


@respx.mock
def test_successful_charge(client: PaymentClient) -> None:
    transaction_id = uuid.uuid4()
    route = respx.post(URL).mock(
        return_value=httpx.Response(
            200,
            json={
                "success": True,
                "data": {
                    "transaction_id": str(transaction_id),
                    "card_token": "pm_abc",
                    "amount": "89.99",
                },
                "error": None,
            },
        )
    )

    result = client.charge(uuid.uuid4(), Decimal("89.99"), "subscription:SIP", card_token="pm_abc")

    assert result.transaction_id == transaction_id
    assert result.card_token == "pm_abc"
    assert route.calls.last.request.headers["X-Internal-Token"] == "token"


@respx.mock
def test_decline_keeps_payment_service_error(client: PaymentClient) -> None:
    respx.post(URL).mock(
        return_value=httpx.Response(
            402,
            json={
                "success": False,
                "data": None,
                "error": {"code": "PAYMENT_DECLINED", "message": "Declined.", "details": None},
            },
        )
    )

    with pytest.raises(AppError) as exc_info:
        client.charge(uuid.uuid4(), Decimal("1.00"), "x", card_token="pm_abc")

    assert (exc_info.value.status_code, exc_info.value.code) == (402, "PAYMENT_DECLINED")


@respx.mock
def test_unreachable_payment_service(client: PaymentClient) -> None:
    respx.post(URL).mock(side_effect=httpx.ConnectError("refused"))

    with pytest.raises(ServiceUnavailableError):
        client.charge(uuid.uuid4(), Decimal("1.00"), "x", card_token="pm_abc")

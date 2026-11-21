"""Calls the payment service's internal charge endpoint."""

import uuid
from dataclasses import dataclass
from decimal import Decimal
from functools import lru_cache
from typing import Any

from brewpass_common.internal_client import InternalClient
from commerce_service.config import get_settings


@dataclass(frozen=True)
class ChargeResult:
    transaction_id: uuid.UUID
    card_token: str
    amount: Decimal


class PaymentClient:
    def __init__(self, client: InternalClient) -> None:
        self._client = client

    def charge(
        self,
        user_id: uuid.UUID,
        amount: Decimal,
        description: str,
        *,
        currency: str = "TRY",
        card: dict[str, Any] | None = None,
        card_token: str | None = None,
    ) -> ChargeResult:
        """Charge a card or a saved card token.

        Raises the payment service's errors unchanged, e.g. `402 PAYMENT_DECLINED` or
        `422 VALIDATION_ERROR` for an invalid card, and `503` if it cannot be reached.
        """
        data = self._client.post(
            "/internal/payments/charge",
            json={
                "user_id": str(user_id),
                "amount": str(amount),
                "currency": currency,
                "description": description,
                "card": card,
                "card_token": card_token,
            },
        )
        return ChargeResult(
            transaction_id=uuid.UUID(data["transaction_id"]),
            card_token=data["card_token"],
            amount=Decimal(data["amount"]),
        )


@lru_cache
def get_payment_client() -> PaymentClient:
    settings = get_settings()
    return PaymentClient(InternalClient(settings.payment_service_url, settings.internal_token))

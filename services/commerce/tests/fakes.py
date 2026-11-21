import uuid
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

from brewpass_common.errors import PaymentRequiredError, ServiceUnavailableError
from commerce_service.clients.payment_client import ChargeResult


@dataclass
class Charge:
    user_id: uuid.UUID
    amount: Decimal
    description: str
    card: dict[str, Any] | None
    card_token: str | None


@dataclass
class FakePayments:
    """Stands in for the payment service: records charges and can decline or be unavailable."""

    decline: bool = False
    unavailable: bool = False
    charges: list[Charge] = field(default_factory=list)

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
        if self.unavailable:
            raise ServiceUnavailableError()
        self.charges.append(Charge(user_id, amount, description, card, card_token))
        declining_card = card is not None and card["number"].endswith("0002")
        if self.decline or declining_card:
            raise PaymentRequiredError("Payment declined. Try another card.")
        token = card_token or f"pm_test_{len(self.charges)}"
        return ChargeResult(transaction_id=uuid.uuid4(), card_token=token, amount=amount)

    @property
    def last(self) -> Charge:
        return self.charges[-1]

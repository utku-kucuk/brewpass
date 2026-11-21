import re
import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Annotated, Self

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    SecretStr,
    StringConstraints,
    model_validator,
)

from payment_service.models import PaymentStatus

_DIGITS = re.compile(r"\D")


def luhn_valid(number: str) -> bool:
    total = 0
    for index, char in enumerate(reversed(number)):
        digit = int(char)
        if index % 2 == 1:
            digit *= 2
            if digit > 9:
                digit -= 9
        total += digit
    return total % 10 == 0


def _card_number(value: SecretStr) -> SecretStr:
    digits = _DIGITS.sub("", value.get_secret_value())
    if not 13 <= len(digits) <= 19 or not luhn_valid(digits):
        raise ValueError("Card number is invalid.")
    return SecretStr(digits)


def _cvc(value: SecretStr) -> SecretStr:
    cvc = value.get_secret_value()
    if not (cvc.isdigit() and 3 <= len(cvc) <= 4):
        raise ValueError("CVC must be 3 or 4 digits.")
    return value


CardNumber = Annotated[SecretStr, AfterValidator(_card_number)]
Cvc = Annotated[SecretStr, AfterValidator(_cvc)]
HolderName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=100)]


class CardIn(BaseModel):
    """Raw card details. Only ever held in memory; never stored or logged."""

    number: CardNumber
    exp_month: int = Field(ge=1, le=12)
    exp_year: int = Field(ge=2000, le=2100)
    cvc: Cvc
    holder_name: HolderName

    @model_validator(mode="after")
    def _not_expired(self) -> Self:
        now = datetime.now(UTC)
        if (self.exp_year, self.exp_month) < (now.year, now.month):
            raise ValueError("Card has expired.")
        return self


class ChargeIn(BaseModel):
    """Internal charge request from another service. Exactly one of `card` / `card_token`."""

    model_config = ConfigDict(extra="forbid")

    user_id: uuid.UUID
    amount: Decimal = Field(gt=0, max_digits=10, decimal_places=2)
    currency: Annotated[str, StringConstraints(pattern=r"^[A-Z]{3}$")] = "TRY"
    description: Annotated[str, StringConstraints(min_length=1, max_length=120)]
    card: CardIn | None = None
    card_token: str | None = None

    @model_validator(mode="after")
    def _one_payment_source(self) -> Self:
        if (self.card is None) == (self.card_token is None):
            raise ValueError("Provide either card or card_token.")
        return self


class ChargeOut(BaseModel):
    transaction_id: uuid.UUID
    status: PaymentStatus
    amount: Decimal
    currency: str
    card_token: str
    card_last4: str
    card_brand: str
    created_at: datetime


class PaymentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    transaction_id: uuid.UUID
    status: PaymentStatus
    amount: Decimal
    currency: str
    description: str
    card_last4: str | None
    failure_reason: str | None
    created_at: datetime

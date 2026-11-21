"""BrewPass Pay: a mock card gateway.

- `4000 0000 0000 0002` always declines (also on later charges with its saved token).
- Any other valid card (Luhn, not expired) succeeds, e.g. `4242 4242 4242 4242`.
Every attempt, successful or not, is stored so it shows up in the payment history.
"""

import logging
import secrets
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from brewpass_common.errors import NotFoundError, PaymentRequiredError
from payment_service.models import Payment, PaymentMethod, PaymentStatus
from payment_service.schemas.payment import CardIn, ChargeIn, ChargeOut, PaymentOut

logger = logging.getLogger(__name__)

DECLINING_TEST_CARD = "4000000000000002"
DECLINE_REASON = "Card declined by the issuer."


def card_brand(number: str) -> str:
    if number.startswith("4"):
        return "VISA"
    if number[:2] in {"51", "52", "53", "54", "55"} or "2221" <= number[:4] <= "2720":
        return "MASTERCARD"
    if number[:2] in {"34", "37"}:
        return "AMEX"
    if number.startswith("9792"):
        return "TROY"
    return "CARD"


class PaymentService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def _save_card(self, user_id: uuid.UUID, card: CardIn) -> PaymentMethod:
        number = card.number.get_secret_value()
        method = PaymentMethod(
            user_id=user_id,
            token=f"pm_{secrets.token_urlsafe(24)}",
            brand=card_brand(number),
            last4=number[-4:],
            exp_month=card.exp_month,
            exp_year=card.exp_year,
            always_declines=number == DECLINING_TEST_CARD,
        )
        self.session.add(method)
        self.session.flush()
        return method

    def _saved_card(self, user_id: uuid.UUID, token: str) -> PaymentMethod:
        method = self.session.scalar(
            select(PaymentMethod).where(
                PaymentMethod.token == token, PaymentMethod.user_id == user_id
            )
        )
        if method is None:
            raise NotFoundError("Saved card not found.", code="PAYMENT_METHOD_NOT_FOUND")
        return method

    def charge(self, data: ChargeIn) -> ChargeOut:
        if data.card is not None:
            method = self._save_card(data.user_id, data.card)
        else:
            assert data.card_token is not None
            method = self._saved_card(data.user_id, data.card_token)

        declined = method.always_declines
        payment = Payment(
            user_id=data.user_id,
            description=data.description,
            amount=data.amount,
            currency=data.currency,
            status=PaymentStatus.FAILED if declined else PaymentStatus.SUCCEEDED,
            payment_method_id=method.id,
            card_last4=method.last4,
            failure_reason=DECLINE_REASON if declined else None,
        )
        self.session.add(payment)
        self.session.commit()

        logger.info(
            "Payment processed",
            extra={
                "transaction_id": str(payment.transaction_id),
                "status": payment.status.value,
                "amount": str(payment.amount),
            },
        )
        if declined:
            raise PaymentRequiredError(
                "Payment declined. Try another card.",
                details={"transaction_id": str(payment.transaction_id)},
            )

        return ChargeOut(
            transaction_id=payment.transaction_id,
            status=payment.status,
            amount=payment.amount,
            currency=payment.currency,
            card_token=method.token,
            card_last4=method.last4,
            card_brand=method.brand,
            created_at=payment.created_at,
        )

    def history(self, user_id: uuid.UUID, limit: int = 50) -> list[PaymentOut]:
        payments = self.session.scalars(
            select(Payment)
            .where(Payment.user_id == user_id)
            .order_by(Payment.created_at.desc(), Payment.id.desc())
            .limit(limit)
        )
        return [PaymentOut.model_validate(p) for p in payments]

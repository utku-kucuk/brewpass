import uuid
from datetime import datetime
from decimal import Decimal
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, SecretStr, StringConstraints

from commerce_service.models import Plan, PlanCode, Subscription, SubscriptionStatus


class PlanOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    code: PlanCode
    name: str
    description: str | None
    price: Decimal
    currency: str
    monthly_credits: int | None = Field(description="Drinks per month; null means unlimited.")
    guest_credits: int
    priority_pickup: bool
    is_unlimited: bool

    @classmethod
    def from_plan(cls, plan: Plan) -> "PlanOut":
        return cls.model_validate(plan)


class CardIn(BaseModel):
    """Card details, forwarded to the payment service as-is (which validates them).

    Secrets are wrapped so they never appear in logs or reprs.
    """

    number: SecretStr
    exp_month: int
    exp_year: int
    cvc: SecretStr
    holder_name: Annotated[str, StringConstraints(strip_whitespace=True, max_length=100)]

    def to_payment_payload(self) -> dict[str, Any]:
        return {
            "number": self.number.get_secret_value(),
            "exp_month": self.exp_month,
            "exp_year": self.exp_year,
            "cvc": self.cvc.get_secret_value(),
            "holder_name": self.holder_name,
        }


class SubscribeIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    plan_code: PlanCode
    card: CardIn


class ResumeIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    card: CardIn | None = Field(default=None, description="New card; omit to retry the saved card.")


class ChangePlanIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    plan_code: PlanCode


class SubscriptionOut(BaseModel):
    id: uuid.UUID
    status: SubscriptionStatus
    plan: PlanOut
    remaining_credits: int | None = Field(description="null means unlimited.")
    remaining_guest_credits: int
    current_period_start: datetime
    current_period_end: datetime
    pending_plan: PlanOut | None = Field(description="Downgrade that applies at renewal.")
    payment_transaction_id: uuid.UUID | None
    cancelled_at: datetime | None

    @classmethod
    def from_subscription(cls, sub: Subscription) -> "SubscriptionOut":
        return cls(
            id=sub.id,
            status=sub.status,
            plan=PlanOut.from_plan(sub.plan),
            remaining_credits=sub.remaining_credits,
            remaining_guest_credits=sub.remaining_guest_credits,
            current_period_start=sub.started_at,
            current_period_end=sub.expires_at,
            pending_plan=PlanOut.from_plan(sub.pending_plan) if sub.pending_plan else None,
            payment_transaction_id=sub.payment_transaction_id,
            cancelled_at=sub.cancelled_at,
        )


class RenewalReport(BaseModel):
    renewed: int
    paused: int

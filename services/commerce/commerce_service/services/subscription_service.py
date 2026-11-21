"""Subscription lifecycle: subscribe, renew, upgrade, downgrade, resume and cancel.

Rules
- One live (ACTIVE or PAUSED) subscription per member; periods last one calendar month.
- Renewal happens lazily whenever the subscription is read or changed, and in bulk through
  `renew_due` (cron-ready). It charges the saved card; a declined renewal pauses the pass.
- Upgrades apply immediately: the price difference is charged and the extra drinks are added to
  this period. Downgrades are scheduled and apply at the next renewal.
- Cancelling ends the pass immediately, without a refund.
"""

import calendar
import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from brewpass_common.errors import AppError, ConflictError, NotFoundError
from commerce_service.clients.payment_client import PaymentClient
from commerce_service.models import Plan, PlanCode, Subscription, SubscriptionStatus
from commerce_service.repositories.subscription_repository import (
    PlanRepository,
    SubscriptionRepository,
)
from commerce_service.schemas.subscription import (
    CardIn,
    PlanOut,
    RenewalReport,
    SubscriptionOut,
)

logger = logging.getLogger(__name__)


def utcnow() -> datetime:
    return datetime.now(UTC)


def add_month(moment: datetime) -> datetime:
    """Same day next month, clamped to the month's last day (Jan 31 -> Feb 28/29)."""
    year, month = (moment.year + 1, 1) if moment.month == 12 else (moment.year, moment.month + 1)
    day = min(moment.day, calendar.monthrange(year, month)[1])
    return moment.replace(year=year, month=month, day=day)


class SubscriptionService:
    def __init__(self, session: Session, payments: PaymentClient) -> None:
        self.session = session
        self.payments = payments
        self.plans = PlanRepository(session)
        self.subscriptions = SubscriptionRepository(session)

    # --- Queries ---------------------------------------------------------------------------

    def list_plans(self) -> list[PlanOut]:
        return [PlanOut.from_plan(plan) for plan in self.plans.list_active()]

    def _plan(self, code: PlanCode) -> Plan:
        plan = self.plans.get_active_by_code(code)
        if plan is None:
            raise NotFoundError("This pass is not available.", code="PLAN_NOT_FOUND")
        return plan

    def _live(self, user_id: uuid.UUID) -> Subscription:
        subscription = self.subscriptions.get_live(user_id, lock=True)
        if subscription is None:
            raise NotFoundError("You don't have an active pass.", code="NO_ACTIVE_SUBSCRIPTION")
        return subscription

    def current(self, user_id: uuid.UUID) -> SubscriptionOut:
        subscription = self._live(user_id)
        self.ensure_current_period(subscription)
        self.session.commit()
        return SubscriptionOut.from_subscription(subscription)

    # --- Subscribe -------------------------------------------------------------------------

    def subscribe(self, user_id: uuid.UUID, plan_code: PlanCode, card: CardIn) -> SubscriptionOut:
        plan = self._plan(plan_code)
        if self.subscriptions.get_live(user_id, lock=True) is not None:
            raise ConflictError("You already have a pass.", code="SUBSCRIPTION_EXISTS")

        charge = self.payments.charge(
            user_id,
            plan.price,
            f"subscription:{plan.code.value}",
            currency=plan.currency,
            card=card.to_payment_payload(),
        )
        now = utcnow()
        subscription = Subscription(
            user_id=user_id,
            plan_id=plan.id,
            status=SubscriptionStatus.ACTIVE,
            remaining_credits=plan.monthly_credits,
            remaining_guest_credits=plan.guest_credits,
            started_at=now,
            expires_at=add_month(now),
            payment_transaction_id=charge.transaction_id,
            card_token=charge.card_token,
        )
        self.session.add(subscription)
        try:
            self.session.commit()
        except IntegrityError as exc:
            # A concurrent request created the pass first; the partial unique index caught it.
            self.session.rollback()
            logger.warning(
                "Duplicate subscription after payment",
                extra={"user_id": str(user_id), "transaction_id": str(charge.transaction_id)},
            )
            raise ConflictError("You already have a pass.", code="SUBSCRIPTION_EXISTS") from exc
        self.session.refresh(subscription)
        return SubscriptionOut.from_subscription(subscription)

    # --- Renewal ---------------------------------------------------------------------------

    def _start_period(self, subscription: Subscription, plan: Plan, start: datetime) -> None:
        subscription.plan_id = plan.id
        subscription.plan = plan
        subscription.pending_plan_id = None
        subscription.pending_plan = None
        subscription.started_at = start
        subscription.expires_at = add_month(start)
        subscription.remaining_credits = plan.monthly_credits
        subscription.remaining_guest_credits = plan.guest_credits
        subscription.status = SubscriptionStatus.ACTIVE

    def ensure_current_period(self, subscription: Subscription) -> None:
        """Renew an expired active pass with the saved card; pause it if the charge fails."""
        now = utcnow()
        if subscription.status != SubscriptionStatus.ACTIVE or subscription.expires_at > now:
            return

        plan = subscription.pending_plan or subscription.plan
        try:
            charge = self.payments.charge(
                subscription.user_id,
                plan.price,
                f"renewal:{plan.code.value}",
                currency=plan.currency,
                card_token=subscription.card_token,
            )
        except AppError as exc:
            if exc.status_code >= 500:
                raise  # payment service unavailable: try again later, keep the pass as is
            subscription.status = SubscriptionStatus.PAUSED
            logger.info(
                "Renewal declined; subscription paused",
                extra={"subscription_id": str(subscription.id), "code": exc.code},
            )
            return

        # Continue the billing cycle unless more than one period was missed.
        start = subscription.expires_at if now < add_month(subscription.expires_at) else now
        self._start_period(subscription, plan, start)
        subscription.payment_transaction_id = charge.transaction_id

    def renew_due(self) -> RenewalReport:
        renewed = paused = 0
        for subscription in self.subscriptions.due_for_renewal(utcnow()):
            self.ensure_current_period(subscription)
            if subscription.status == SubscriptionStatus.PAUSED:
                paused += 1
            else:
                renewed += 1
        self.session.commit()
        return RenewalReport(renewed=renewed, paused=paused)

    def resume(self, user_id: uuid.UUID, card: CardIn | None) -> SubscriptionOut:
        """Reactivate a paused pass by paying for a new period (new card or saved card)."""
        subscription = self._live(user_id)
        if subscription.status != SubscriptionStatus.PAUSED:
            raise ConflictError("Your pass is already active.", code="SUBSCRIPTION_NOT_PAUSED")

        plan = subscription.pending_plan or subscription.plan
        charge = self.payments.charge(
            user_id,
            plan.price,
            f"resume:{plan.code.value}",
            currency=plan.currency,
            card=card.to_payment_payload() if card else None,
            card_token=None if card else subscription.card_token,
        )
        self._start_period(subscription, plan, utcnow())
        subscription.payment_transaction_id = charge.transaction_id
        subscription.card_token = charge.card_token
        self.session.commit()
        return SubscriptionOut.from_subscription(subscription)

    # --- Plan changes ----------------------------------------------------------------------

    def change_plan(self, user_id: uuid.UUID, plan_code: PlanCode) -> SubscriptionOut:
        subscription = self._live(user_id)
        self.ensure_current_period(subscription)
        if subscription.status != SubscriptionStatus.ACTIVE:
            self.session.commit()
            raise ConflictError(
                "Your pass is paused. Resume it before changing plans.",
                code="SUBSCRIPTION_PAUSED",
            )

        current = subscription.plan
        target = self._plan(plan_code)

        if target.id == current.id:
            if subscription.pending_plan_id is None:
                raise ConflictError("You are already on this pass.", code="SAME_PLAN")
            # Choosing the current plan again cancels a scheduled downgrade.
            subscription.pending_plan_id = None
            subscription.pending_plan = None
        elif target.price > current.price:
            self._upgrade(subscription, current, target)
        else:
            subscription.pending_plan_id = target.id
            subscription.pending_plan = target

        self.session.commit()
        return SubscriptionOut.from_subscription(subscription)

    def _upgrade(self, subscription: Subscription, current: Plan, target: Plan) -> None:
        charge = self.payments.charge(
            subscription.user_id,
            target.price - current.price,
            f"upgrade:{current.code.value}->{target.code.value}",
            currency=target.currency,
            card_token=subscription.card_token,
        )
        if target.monthly_credits is None:
            subscription.remaining_credits = None
        elif subscription.remaining_credits is not None and current.monthly_credits is not None:
            subscription.remaining_credits += target.monthly_credits - current.monthly_credits
        subscription.remaining_guest_credits += max(0, target.guest_credits - current.guest_credits)
        subscription.plan_id = target.id
        subscription.plan = target
        subscription.pending_plan_id = None
        subscription.pending_plan = None
        subscription.payment_transaction_id = charge.transaction_id

    # --- Cancel ----------------------------------------------------------------------------

    def cancel(self, user_id: uuid.UUID) -> SubscriptionOut:
        subscription = self._live(user_id)
        subscription.status = SubscriptionStatus.CANCELLED
        subscription.cancelled_at = utcnow()
        subscription.pending_plan_id = None
        subscription.pending_plan = None
        self.session.commit()
        return SubscriptionOut.from_subscription(subscription)

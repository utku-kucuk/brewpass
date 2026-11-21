from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from brewpass_common.responses import ApiResponse, ok
from brewpass_common.security import Principal, UserRole, require_internal_token, require_roles
from commerce_service.clients.payment_client import PaymentClient, get_payment_client
from commerce_service.db import get_db
from commerce_service.schemas.subscription import (
    ChangePlanIn,
    PlanOut,
    RenewalReport,
    ResumeIn,
    SubscribeIn,
    SubscriptionOut,
)
from commerce_service.services.subscription_service import SubscriptionService

router = APIRouter(prefix="/api/v1/subscriptions", tags=["subscriptions"])
internal_router = APIRouter(
    prefix="/internal/subscriptions",
    tags=["internal"],
    dependencies=[Depends(require_internal_token)],
)

Customer = Annotated[Principal, Depends(require_roles(UserRole.CUSTOMER))]


def get_subscription_service(
    db: Annotated[Session, Depends(get_db)],
    payments: Annotated[PaymentClient, Depends(get_payment_client)],
) -> SubscriptionService:
    return SubscriptionService(db, payments)


Service = Annotated[SubscriptionService, Depends(get_subscription_service)]


@router.get("/plans", response_model=ApiResponse[list[PlanOut]], summary="Available passes")
def list_plans(service: Service) -> ApiResponse[list[PlanOut]]:
    return ok(service.list_plans())


@router.post(
    "",
    response_model=ApiResponse[SubscriptionOut],
    status_code=201,
    summary="Buy a pass",
    description="Charges the card with BrewPass Pay. Test cards: `4242 4242 4242 4242` succeeds, "
    "`4000 0000 0000 0002` is declined.",
)
def subscribe(body: SubscribeIn, user: Customer, service: Service) -> ApiResponse[SubscriptionOut]:
    return ok(service.subscribe(user.user_id, body.plan_code, body.card))


@router.get("/me", response_model=ApiResponse[SubscriptionOut], summary="My current pass")
def get_my_subscription(user: Customer, service: Service) -> ApiResponse[SubscriptionOut]:
    return ok(service.current(user.user_id))


@router.patch(
    "/me",
    response_model=ApiResponse[SubscriptionOut],
    summary="Upgrade or downgrade",
    description="Upgrades apply now and charge the price difference; downgrades apply at the "
    "next renewal. Picking the current pass again cancels a scheduled downgrade.",
)
def change_plan(
    body: ChangePlanIn, user: Customer, service: Service
) -> ApiResponse[SubscriptionOut]:
    return ok(service.change_plan(user.user_id, body.plan_code))


@router.post(
    "/me/resume",
    response_model=ApiResponse[SubscriptionOut],
    summary="Resume a paused pass",
)
def resume(body: ResumeIn, user: Customer, service: Service) -> ApiResponse[SubscriptionOut]:
    return ok(service.resume(user.user_id, body.card))


@router.delete("/me", response_model=ApiResponse[SubscriptionOut], summary="Cancel my pass")
def cancel(user: Customer, service: Service) -> ApiResponse[SubscriptionOut]:
    return ok(service.cancel(user.user_id))


@internal_router.post(
    "/renew-due",
    response_model=ApiResponse[RenewalReport],
    summary="Renew every expired active pass (for a scheduler)",
)
def renew_due(service: Service) -> ApiResponse[RenewalReport]:
    return ok(service.renew_due())

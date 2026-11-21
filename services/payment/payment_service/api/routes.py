from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from brewpass_common.responses import ApiResponse, ok
from brewpass_common.security import CurrentPrincipal, require_internal_token
from payment_service.db import get_db
from payment_service.schemas.payment import ChargeIn, ChargeOut, PaymentOut
from payment_service.services.payment_service import PaymentService

DbSession = Annotated[Session, Depends(get_db)]

public_router = APIRouter(prefix="/api/v1/payments", tags=["payments"])
internal_router = APIRouter(
    prefix="/internal/payments",
    tags=["internal"],
    dependencies=[Depends(require_internal_token)],
)


@public_router.get(
    "/me", response_model=ApiResponse[list[PaymentOut]], summary="My payment history"
)
def my_payments(
    principal: CurrentPrincipal,
    db: DbSession,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> ApiResponse[list[PaymentOut]]:
    return ok(PaymentService(db).history(principal.user_id, limit))


@internal_router.post(
    "/charge",
    response_model=ApiResponse[ChargeOut],
    summary="Charge a card or a saved card token",
)
def charge(body: ChargeIn, db: DbSession) -> ApiResponse[ChargeOut]:
    return ok(PaymentService(db).charge(body))

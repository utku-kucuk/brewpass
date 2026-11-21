from fastapi import APIRouter, Request, Response, status

from app.api.deps import DbSession
from app.core.rate_limit import limiter
from app.core.responses import ApiResponse, ok
from app.schemas.auth import AuthOut, RefreshIn, RegisterIn, RegisterOut, TokenOut, VerifyOtpIn
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=ApiResponse[RegisterOut],
    summary="Request a sign-in code",
    description=(
        "Starts sign-up or sign-in for a phone number and sends a one-time code. "
        "Outside production the code is always `1234`."
    ),
)
@limiter.limit("5/minute")
def register(request: Request, body: RegisterIn, db: DbSession) -> ApiResponse[RegisterOut]:
    return ok(AuthService(db).request_otp(body.phone_number))


@router.post(
    "/verify-otp",
    response_model=ApiResponse[AuthOut],
    summary="Verify the code and receive tokens",
)
@limiter.limit("10/minute")
def verify_otp(request: Request, body: VerifyOtpIn, db: DbSession) -> ApiResponse[AuthOut]:
    return ok(AuthService(db).verify_otp(body.phone_number, body.code))


@router.post(
    "/refresh",
    response_model=ApiResponse[TokenOut],
    summary="Exchange a refresh token for a new token pair",
)
def refresh(body: RefreshIn, db: DbSession) -> ApiResponse[TokenOut]:
    return ok(AuthService(db).refresh(body.refresh_token))


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    summary="Revoke a refresh token",
)
def logout(body: RefreshIn, db: DbSession) -> Response:
    AuthService(db).logout(body.refresh_token)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

"""Access token verification and the principal (caller identity) dependencies.

Only the auth service holds the private key and issues tokens. Every service verifies them locally
with the public key, so no network call to the auth service is needed per request.
"""

import enum
import hmac
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from functools import lru_cache
from typing import Annotated

import jwt
from fastapi import Depends, Header
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from brewpass_common.config import ServiceSettings
from brewpass_common.errors import ForbiddenError, UnauthorizedError

ACCESS_TOKEN_TYPE = "access"


class UserRole(enum.StrEnum):
    CUSTOMER = "CUSTOMER"
    SHOP_OWNER = "SHOP_OWNER"
    ADMIN = "ADMIN"


class InvalidTokenError(Exception):
    pass


@dataclass(frozen=True)
class Principal:
    """The authenticated caller, as stated by a verified access token."""

    user_id: uuid.UUID
    role: UserRole


def decode_access_token(token: str, settings: ServiceSettings) -> Principal:
    if not settings.jwt_public_key:
        raise InvalidTokenError("Token verification is not configured.")
    try:
        payload = jwt.decode(
            token,
            settings.jwt_public_key,
            algorithms=[settings.jwt_algorithm],
            issuer=settings.jwt_issuer,
            options={"require": ["sub", "exp", "iss", "type", "role"]},
        )
    except jwt.ExpiredSignatureError as exc:
        raise InvalidTokenError("Access token has expired.") from exc
    except jwt.PyJWTError as exc:
        raise InvalidTokenError("Access token is invalid.") from exc

    if payload["type"] != ACCESS_TOKEN_TYPE:
        raise InvalidTokenError("Access token is invalid.")
    try:
        return Principal(user_id=uuid.UUID(payload["sub"]), role=UserRole(payload["role"]))
    except ValueError as exc:
        raise InvalidTokenError("Access token is invalid.") from exc


@lru_cache
def _default_settings() -> ServiceSettings:
    return ServiceSettings()


def get_settings_dependency() -> ServiceSettings:
    """Overridden by each service with its own settings (see `create_service_app`)."""
    return _default_settings()


_bearer = HTTPBearer(auto_error=False, description="Access token from /auth/verify-otp")


def get_principal(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    settings: Annotated[ServiceSettings, Depends(get_settings_dependency)],
) -> Principal:
    if credentials is None:
        raise UnauthorizedError("Sign in to continue.")
    try:
        return decode_access_token(credentials.credentials, settings)
    except InvalidTokenError as exc:
        raise UnauthorizedError(str(exc), code="INVALID_TOKEN") from exc


CurrentPrincipal = Annotated[Principal, Depends(get_principal)]


def require_roles(*roles: UserRole) -> Callable[[Principal], Principal]:
    """Dependency factory: `Depends(require_roles(UserRole.SHOP_OWNER))`."""

    def dependency(principal: CurrentPrincipal) -> Principal:
        if principal.role not in roles:
            raise ForbiddenError()
        return principal

    return dependency


def require_internal_token(
    settings: Annotated[ServiceSettings, Depends(get_settings_dependency)],
    x_internal_token: Annotated[str | None, Header()] = None,
) -> None:
    """Guards `/internal` routes that only other services may call."""
    if x_internal_token is None or not hmac.compare_digest(
        x_internal_token.encode(), settings.internal_token.encode()
    ):
        raise UnauthorizedError("Internal endpoint.", code="INTERNAL_ONLY")

"""Token and secret helpers: JWT access tokens, opaque refresh tokens and keyed hashes."""

import hashlib
import hmac
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt

from app.core.config import get_settings
from app.models.enums import UserRole

ACCESS_TOKEN_TYPE = "access"


class InvalidTokenError(Exception):
    pass


def utcnow() -> datetime:
    return datetime.now(UTC)


def keyed_hash(value: str) -> str:
    """HMAC-SHA256 of a secret value (OTP code, refresh token) using the server secret."""
    key = get_settings().jwt_secret_key.encode()
    return hmac.new(key, value.encode(), hashlib.sha256).hexdigest()


def hashes_match(value: str, expected_hash: str) -> bool:
    return hmac.compare_digest(keyed_hash(value), expected_hash)


def new_refresh_token() -> str:
    return secrets.token_urlsafe(48)


def create_access_token(user_id: uuid.UUID, role: UserRole) -> tuple[str, int]:
    """Return a signed JWT and its lifetime in seconds."""
    settings = get_settings()
    ttl = timedelta(minutes=settings.access_token_ttl_minutes)
    now = utcnow()
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "role": role.value,
        "type": ACCESS_TOKEN_TYPE,
        "iat": now,
        "exp": now + ttl,
    }
    token = jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    return token, int(ttl.total_seconds())


def decode_access_token(token: str) -> uuid.UUID:
    """Validate a JWT access token and return the user id it was issued for."""
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
            options={"require": ["sub", "exp", "type"]},
        )
    except jwt.ExpiredSignatureError as exc:
        raise InvalidTokenError("Access token has expired.") from exc
    except jwt.PyJWTError as exc:
        raise InvalidTokenError("Access token is invalid.") from exc

    if payload.get("type") != ACCESS_TOKEN_TYPE:
        raise InvalidTokenError("Access token is invalid.")
    try:
        return uuid.UUID(payload["sub"])
    except ValueError as exc:
        raise InvalidTokenError("Access token is invalid.") from exc

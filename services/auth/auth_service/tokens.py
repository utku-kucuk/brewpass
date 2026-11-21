"""Issuing access tokens (RS256) and hashing secrets at rest.

Verification lives in `brewpass_common.security`, shared by every service.
"""

import hashlib
import hmac
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt

from auth_service.config import get_settings
from brewpass_common.security import ACCESS_TOKEN_TYPE, UserRole


def utcnow() -> datetime:
    return datetime.now(UTC)


def keyed_hash(value: str) -> str:
    """HMAC-SHA256 of a secret value (OTP code, refresh token) using the server secret."""
    key = get_settings().hash_secret.encode()
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
        "iss": settings.jwt_issuer,
        "iat": now,
        "exp": now + ttl,
    }
    assert settings.jwt_private_key is not None
    token = jwt.encode(payload, settings.jwt_private_key, algorithm=settings.jwt_algorithm)
    return token, int(ttl.total_seconds())

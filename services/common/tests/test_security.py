import uuid
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
import pytest
from fastapi import APIRouter, Depends
from fastapi.testclient import TestClient

from brewpass_common.app import create_service_app
from brewpass_common.config import ServiceSettings
from brewpass_common.security import (
    CurrentPrincipal,
    UserRole,
    require_internal_token,
    require_roles,
)
from brewpass_common.testing import generate_key_pair

KEYS = generate_key_pair()
OTHER_KEYS = generate_key_pair()
USER_ID = uuid.uuid4()

router = APIRouter()


@router.get("/api/v1/whoami")
def whoami(principal: CurrentPrincipal) -> dict[str, str]:
    return {"user_id": str(principal.user_id), "role": principal.role.value}


@router.get("/api/v1/owner-only", dependencies=[Depends(require_roles(UserRole.SHOP_OWNER))])
def owner_only() -> dict[str, bool]:
    return {"ok": True}


@router.get("/internal/ping", dependencies=[Depends(require_internal_token)])
def internal_ping() -> dict[str, bool]:
    return {"ok": True}


def make_token(private_pem: str = KEYS.private_pem, **overrides: Any) -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": str(USER_ID),
        "role": "CUSTOMER",
        "type": "access",
        "iss": "brewpass-auth",
        "iat": now,
        "exp": now + timedelta(minutes=5),
        **overrides,
    }
    return jwt.encode(payload, private_pem, algorithm="RS256")


@pytest.fixture
def client() -> Iterator[TestClient]:
    settings = ServiceSettings(
        service_name="sample",
        environment="test",
        jwt_public_key=KEYS.public_pem,
        internal_token="secret-internal-token",
    )
    app = create_service_app(settings, title="Sample", description="", routers=[router])
    with TestClient(app) as test_client:
        yield test_client


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_valid_token_yields_principal(client: TestClient) -> None:
    response = client.get("/api/v1/whoami", headers=bearer(make_token()))

    assert response.status_code == 200
    assert response.json() == {"user_id": str(USER_ID), "role": "CUSTOMER"}


def test_missing_token_is_unauthorized(client: TestClient) -> None:
    response = client.get("/api/v1/whoami")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"
    assert response.headers["WWW-Authenticate"] == "Bearer"


@pytest.mark.parametrize(
    ("token", "message"),
    [
        (make_token(exp=datetime.now(UTC) - timedelta(seconds=1)), "Access token has expired."),
        (make_token(private_pem=OTHER_KEYS.private_pem), "Access token is invalid."),
        (make_token(iss="someone-else"), "Access token is invalid."),
        (make_token(type="refresh"), "Access token is invalid."),
        (make_token(role="SUPERUSER"), "Access token is invalid."),
        ("not-a-jwt", "Access token is invalid."),
    ],
    ids=["expired", "wrong-key", "wrong-issuer", "wrong-type", "unknown-role", "garbage"],
)
def test_bad_tokens_are_rejected(client: TestClient, token: str, message: str) -> None:
    response = client.get("/api/v1/whoami", headers=bearer(token))

    assert response.status_code == 401
    error = response.json()["error"]
    assert (error["code"], error["message"]) == ("INVALID_TOKEN", message)


def test_hs256_token_signed_with_public_key_is_rejected(client: TestClient) -> None:
    """Algorithm confusion: a token 'signed' with the public key as an HMAC secret must fail."""
    payload = jwt.decode(make_token(), options={"verify_signature": False})
    forged = jwt.api_jws.PyJWS().encode(
        jwt.utils.force_bytes(__import__("json").dumps(payload, default=str)),
        b"x" * 32,
        algorithm="HS256",
    )

    response = client.get("/api/v1/whoami", headers=bearer(forged))

    assert response.status_code == 401


def test_role_guard(client: TestClient) -> None:
    customer = client.get("/api/v1/owner-only", headers=bearer(make_token()))
    owner = client.get("/api/v1/owner-only", headers=bearer(make_token(role="SHOP_OWNER")))

    assert customer.status_code == 403
    assert owner.status_code == 200


def test_internal_routes_require_internal_token(client: TestClient) -> None:
    assert client.get("/internal/ping").status_code == 401
    assert client.get("/internal/ping", headers={"X-Internal-Token": "wrong"}).status_code == 401
    assert (
        client.get(
            "/internal/ping", headers={"X-Internal-Token": "secret-internal-token"}
        ).status_code
        == 200
    )


def test_production_requires_real_internal_token() -> None:
    with pytest.raises(ValueError, match="INTERNAL_TOKEN"):
        ServiceSettings(environment="production")

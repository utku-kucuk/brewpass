from datetime import timedelta

import jwt
import pytest
from fastapi import Depends
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from auth_service.config import AuthSettings
from auth_service.models import OtpChallenge, RefreshToken, User
from auth_service.schemas.common import normalize_phone_number
from auth_service.tokens import create_access_token, utcnow
from brewpass_common.security import UserRole, require_roles
from tests.helpers import CUSTOMER_PHONE, auth_header, sign_in

REGISTER = "/api/v1/auth/register"
VERIFY = "/api/v1/auth/verify-otp"
REFRESH = "/api/v1/auth/refresh"
LOGOUT = "/api/v1/auth/logout"


# --- Phone numbers ------------------------------------------------------------------------


@pytest.mark.parametrize(
    "raw",
    ["+905321112233", "05321112233", "5321112233", "0090 532 111 22 33", "(0532) 111-22-33"],
)
def test_phone_numbers_are_normalized_to_e164(raw: str) -> None:
    assert normalize_phone_number(raw) == "+905321112233"


@pytest.mark.parametrize("raw", ["12345", "+905321112", "02121112233", "+15551234567", "abc"])
def test_invalid_phone_numbers_are_rejected(client: TestClient, raw: str) -> None:
    response = client.post(REGISTER, json={"phone_number": raw})

    assert response.status_code == 422
    assert response.json()["error"]["details"][0]["field"] == "phone_number"


# --- Register ------------------------------------------------------------------------------


def test_register_creates_customer_and_never_returns_the_code(
    client: TestClient, db_session: Session
) -> None:
    response = client.post(REGISTER, json={"phone_number": "0532 111 22 33"})

    assert response.status_code == 200
    data = response.json()["data"]
    assert data == {"phone_number": CUSTOMER_PHONE, "is_new_user": True, "otp_expires_in": 300}
    assert "1234" not in response.text

    user = db_session.scalar(select(User).where(User.phone_number == CUSTOMER_PHONE))
    assert user is not None and user.role == UserRole.CUSTOMER


def test_register_existing_user_signs_in(client: TestClient) -> None:
    client.post(REGISTER, json={"phone_number": CUSTOMER_PHONE})

    response = client.post(REGISTER, json={"phone_number": CUSTOMER_PHONE})

    assert response.json()["data"]["is_new_user"] is False


# --- Verify OTP ----------------------------------------------------------------------------


def test_verify_otp_returns_tokens_and_profile_state(client: TestClient) -> None:
    data = sign_in(client)

    assert data["token_type"] == "bearer"
    assert data["expires_in"] == 900
    assert data["access_token"] and data["refresh_token"]
    assert data["user"]["phone_number"] == CUSTOMER_PHONE
    assert data["user"]["profile_completed"] is False


def test_wrong_code_reports_remaining_attempts(client: TestClient) -> None:
    client.post(REGISTER, json={"phone_number": CUSTOMER_PHONE})

    response = client.post(VERIFY, json={"phone_number": CUSTOMER_PHONE, "code": "9999"})

    assert response.status_code == 401
    error = response.json()["error"]
    assert error["code"] == "INVALID_OTP"
    assert error["details"] == {"remaining_attempts": 4}


def test_too_many_wrong_codes_lock_the_challenge(client: TestClient) -> None:
    client.post(REGISTER, json={"phone_number": CUSTOMER_PHONE})
    for _ in range(5):
        client.post(VERIFY, json={"phone_number": CUSTOMER_PHONE, "code": "9999"})

    response = client.post(VERIFY, json={"phone_number": CUSTOMER_PHONE, "code": "1234"})

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "OTP_ATTEMPTS_EXCEEDED"


def test_expired_code_is_rejected(client: TestClient, db_session: Session) -> None:
    client.post(REGISTER, json={"phone_number": CUSTOMER_PHONE})
    challenge = db_session.scalar(
        select(OtpChallenge).where(OtpChallenge.phone_number == CUSTOMER_PHONE)
    )
    assert challenge is not None
    challenge.expires_at = utcnow() - timedelta(seconds=1)
    db_session.flush()

    response = client.post(VERIFY, json={"phone_number": CUSTOMER_PHONE, "code": "1234"})

    assert response.json()["error"]["code"] == "OTP_EXPIRED"


def test_code_can_be_used_only_once(client: TestClient) -> None:
    sign_in(client)

    response = client.post(VERIFY, json={"phone_number": CUSTOMER_PHONE, "code": "1234"})

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_OTP"


def test_verify_without_register_fails(client: TestClient) -> None:
    response = client.post(VERIFY, json={"phone_number": "+905559998877", "code": "1234"})

    assert response.status_code == 401


# --- Access tokens -------------------------------------------------------------------------


def test_protected_endpoint_requires_token(client: TestClient) -> None:
    response = client.get("/api/v1/users/me")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"
    assert response.headers["WWW-Authenticate"] == "Bearer"


def test_malformed_token_is_rejected(client: TestClient) -> None:
    response = client.get("/api/v1/users/me", headers=auth_header("not-a-jwt"))

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_TOKEN"


def test_expired_token_is_rejected(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    user_id = sign_in(client)["user"]["id"]
    monkeypatch.setattr("auth_service.tokens.utcnow", lambda: utcnow() - timedelta(hours=1))
    expired_token, _ = create_access_token(user_id, UserRole.CUSTOMER)
    monkeypatch.undo()

    response = client.get("/api/v1/users/me", headers=auth_header(expired_token))

    assert response.status_code == 401
    assert response.json()["error"]["message"] == "Access token has expired."


def test_role_guard_blocks_other_roles(client: TestClient) -> None:
    @client.app.get(  # type: ignore[attr-defined]
        "/api/v1/_test/owner-only", dependencies=[Depends(require_roles(UserRole.SHOP_OWNER))]
    )
    def owner_only() -> dict[str, bool]:
        return {"ok": True}

    token = sign_in(client)["access_token"]
    response = client.get("/api/v1/_test/owner-only", headers=auth_header(token))

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"


# --- Refresh tokens ------------------------------------------------------------------------


def test_refresh_rotates_tokens(client: TestClient) -> None:
    old_refresh = sign_in(client)["refresh_token"]

    response = client.post(REFRESH, json={"refresh_token": old_refresh})

    assert response.status_code == 200
    new_tokens = response.json()["data"]
    assert new_tokens["refresh_token"] != old_refresh
    me = client.get("/api/v1/users/me", headers=auth_header(new_tokens["access_token"]))
    assert me.status_code == 200


def test_reusing_a_rotated_refresh_token_revokes_all_sessions(
    client: TestClient, db_session: Session
) -> None:
    old_refresh = sign_in(client)["refresh_token"]
    new_refresh = client.post(REFRESH, json={"refresh_token": old_refresh}).json()["data"][
        "refresh_token"
    ]

    reuse = client.post(REFRESH, json={"refresh_token": old_refresh})
    after = client.post(REFRESH, json={"refresh_token": new_refresh})

    assert reuse.status_code == 401
    assert after.status_code == 401
    assert after.json()["error"]["code"] == "INVALID_REFRESH_TOKEN"
    tokens = db_session.scalars(select(RefreshToken)).all()
    assert all(token.revoked_at is not None for token in tokens)


def test_expired_refresh_token_is_rejected(client: TestClient, db_session: Session) -> None:
    refresh_token = sign_in(client)["refresh_token"]
    for token in db_session.scalars(select(RefreshToken)):
        token.expires_at = utcnow() - timedelta(seconds=1)
    db_session.flush()

    response = client.post(REFRESH, json={"refresh_token": refresh_token})

    assert response.status_code == 401


def test_logout_revokes_refresh_token(client: TestClient) -> None:
    refresh_token = sign_in(client)["refresh_token"]

    logout = client.post(LOGOUT, json={"refresh_token": refresh_token})
    response = client.post(REFRESH, json={"refresh_token": refresh_token})

    assert logout.status_code == 204
    assert response.status_code == 401


def test_production_requires_a_real_hash_secret() -> None:
    with pytest.raises(ValueError, match="HASH_SECRET"):
        AuthSettings(environment="production", internal_token="x" * 32)

    settings = AuthSettings(environment="production", internal_token="x" * 32, hash_secret="y" * 48)
    assert settings.is_production


def test_key_pair_is_required(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("JWT_PRIVATE_KEY")

    with pytest.raises(ValueError, match="JWT key pair is missing"):
        AuthSettings()


def test_access_tokens_are_rs256_and_carry_role(client: TestClient) -> None:
    token = sign_in(client)["access_token"]

    header = jwt.get_unverified_header(token)
    claims = jwt.decode(token, options={"verify_signature": False})
    assert header["alg"] == "RS256"
    assert claims["role"] == "CUSTOMER"
    assert claims["iss"] == "brewpass-auth"

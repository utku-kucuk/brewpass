"""Phone + OTP sign-in and token lifecycle.

- `request_otp` creates the user on first contact (as a customer) and issues a new code.
- `verify_otp` checks expiry, attempt limits and single use, then issues an access + refresh pair.
- Refresh tokens rotate on every use. Re-using a revoked token is treated as theft: every refresh
  token of that user is revoked.
"""

import logging
import secrets
from datetime import timedelta

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import ForbiddenError, UnauthorizedError
from app.core.security import (
    create_access_token,
    hashes_match,
    keyed_hash,
    new_refresh_token,
    utcnow,
)
from app.models import RefreshToken, User
from app.repositories.auth_repository import OtpChallengeRepository, RefreshTokenRepository
from app.repositories.user_repository import UserRepository
from app.schemas.auth import AuthOut, RegisterOut, TokenOut
from app.schemas.user import UserOut

logger = logging.getLogger(__name__)

INVALID_OTP = "INVALID_OTP"
OTP_EXPIRED = "OTP_EXPIRED"
OTP_ATTEMPTS_EXCEEDED = "OTP_ATTEMPTS_EXCEEDED"
INVALID_REFRESH_TOKEN = "INVALID_REFRESH_TOKEN"


class AuthService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.settings = get_settings()
        self.users = UserRepository(session)
        self.otps = OtpChallengeRepository(session)
        self.refresh_tokens = RefreshTokenRepository(session)

    # --- OTP -------------------------------------------------------------------------------

    def _generate_code(self) -> str:
        if self.settings.is_production:
            return f"{secrets.randbelow(10**6):06d}"
        return self.settings.otp_mock_code

    def request_otp(self, phone_number: str) -> RegisterOut:
        now = utcnow()
        user = self.users.get_by_phone(phone_number)
        is_new_user = user is None
        if user is None:
            self.users.create(phone_number)

        code = self._generate_code()
        ttl = timedelta(minutes=self.settings.otp_ttl_minutes)
        self.otps.close_open(phone_number, now)
        self.otps.create(phone_number, keyed_hash(code), now + ttl)
        self.session.commit()

        # No SMS provider is integrated; the code is only logged outside production.
        if not self.settings.is_production:
            logger.info("OTP issued", extra={"phone_number": phone_number, "otp": code})

        return RegisterOut(
            phone_number=phone_number,
            is_new_user=is_new_user,
            otp_expires_in=int(ttl.total_seconds()),
        )

    def verify_otp(self, phone_number: str, code: str) -> AuthOut:
        now = utcnow()
        challenge = self.otps.latest_open(phone_number)
        if challenge is None:
            raise UnauthorizedError("Code is invalid. Request a new one.", code=INVALID_OTP)
        if challenge.expires_at <= now:
            raise UnauthorizedError("Code has expired. Request a new one.", code=OTP_EXPIRED)
        if challenge.attempts >= self.settings.otp_max_attempts:
            raise ForbiddenError(
                "Too many wrong attempts. Request a new code.", code=OTP_ATTEMPTS_EXCEEDED
            )

        if not hashes_match(code, challenge.code_hash):
            challenge.attempts += 1
            remaining = self.settings.otp_max_attempts - challenge.attempts
            self.session.commit()
            raise UnauthorizedError(
                "Code is incorrect.", code=INVALID_OTP, details={"remaining_attempts": remaining}
            )

        challenge.consumed_at = now
        user = self.users.get_by_phone(phone_number)
        if user is None:  # pragma: no cover - the user is created together with the challenge
            raise UnauthorizedError("Code is invalid. Request a new one.", code=INVALID_OTP)

        tokens, _ = self._issue_tokens(user)
        self.session.commit()
        return AuthOut(**tokens.model_dump(), user=UserOut.from_user(user))

    # --- Tokens ----------------------------------------------------------------------------

    def _issue_tokens(self, user: User) -> tuple[TokenOut, RefreshToken]:
        access_token, expires_in = create_access_token(user.id, user.role)
        refresh_token = new_refresh_token()
        stored = self.refresh_tokens.create(
            user.id,
            keyed_hash(refresh_token),
            utcnow() + timedelta(days=self.settings.refresh_token_ttl_days),
        )
        tokens = TokenOut(
            access_token=access_token, refresh_token=refresh_token, expires_in=expires_in
        )
        return tokens, stored

    def refresh(self, refresh_token: str) -> TokenOut:
        now = utcnow()
        stored = self.refresh_tokens.get_by_hash(keyed_hash(refresh_token))
        invalid = UnauthorizedError(
            "Session has expired. Sign in again.", code=INVALID_REFRESH_TOKEN
        )
        if stored is None:
            raise invalid

        if stored.revoked_at is not None:
            # A rotated token was used again: assume it leaked and end every session.
            logger.warning("Refresh token reuse detected", extra={"user_id": str(stored.user_id)})
            self.refresh_tokens.revoke_all_for_user(stored.user_id, now)
            self.session.commit()
            raise invalid
        if stored.expires_at <= now:
            raise invalid

        user = self.users.get(stored.user_id)
        if user is None:
            raise invalid

        tokens, new_stored = self._issue_tokens(user)
        stored.revoked_at = now
        stored.replaced_by_id = new_stored.id
        self.session.commit()
        return tokens

    def logout(self, refresh_token: str) -> None:
        stored = self.refresh_tokens.get_by_hash(keyed_hash(refresh_token))
        if stored is not None and stored.revoked_at is None:
            stored.revoked_at = utcnow()
            self.session.commit()

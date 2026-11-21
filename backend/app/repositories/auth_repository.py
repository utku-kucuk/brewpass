import uuid
from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models import OtpChallenge, RefreshToken


class OtpChallengeRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, phone_number: str, code_hash: str, expires_at: datetime) -> OtpChallenge:
        challenge = OtpChallenge(
            phone_number=phone_number, code_hash=code_hash, expires_at=expires_at, attempts=0
        )
        self.session.add(challenge)
        self.session.flush()
        return challenge

    def latest_open(self, phone_number: str) -> OtpChallenge | None:
        """Most recent challenge that has not been used yet, locked for the attempt counter."""
        return self.session.scalar(
            select(OtpChallenge)
            .where(OtpChallenge.phone_number == phone_number, OtpChallenge.consumed_at.is_(None))
            .order_by(OtpChallenge.created_at.desc(), OtpChallenge.id.desc())
            .limit(1)
            .with_for_update()
        )

    def close_open(self, phone_number: str, now: datetime) -> None:
        """Invalidate earlier challenges so only the newest code works."""
        self.session.execute(
            update(OtpChallenge)
            .where(OtpChallenge.phone_number == phone_number, OtpChallenge.consumed_at.is_(None))
            .values(consumed_at=now)
        )


class RefreshTokenRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, user_id: uuid.UUID, token_hash: str, expires_at: datetime) -> RefreshToken:
        token = RefreshToken(user_id=user_id, token_hash=token_hash, expires_at=expires_at)
        self.session.add(token)
        self.session.flush()
        return token

    def get_by_hash(self, token_hash: str) -> RefreshToken | None:
        return self.session.scalar(
            select(RefreshToken).where(RefreshToken.token_hash == token_hash).with_for_update()
        )

    def revoke_all_for_user(self, user_id: uuid.UUID, now: datetime) -> None:
        self.session.execute(
            update(RefreshToken)
            .where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
            .values(revoked_at=now)
        )

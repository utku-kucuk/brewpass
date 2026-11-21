"""Importing this package registers every auth table on `Base.metadata`."""

from auth_service.models.auth import OtpChallenge, RefreshToken
from auth_service.models.user import User

__all__ = ["OtpChallenge", "RefreshToken", "User"]

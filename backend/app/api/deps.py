from collections.abc import Callable
from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.errors import ForbiddenError, UnauthorizedError
from app.core.security import InvalidTokenError, decode_access_token
from app.db.session import get_db
from app.models import User
from app.models.enums import UserRole
from app.repositories.user_repository import UserRepository

DbSession = Annotated[Session, Depends(get_db)]

_bearer = HTTPBearer(auto_error=False, description="Access token from /auth/verify-otp")


def get_current_user(
    db: DbSession,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> User:
    if credentials is None:
        raise UnauthorizedError("Sign in to continue.")
    try:
        user_id = decode_access_token(credentials.credentials)
    except InvalidTokenError as exc:
        raise UnauthorizedError(str(exc), code="INVALID_TOKEN") from exc

    user = UserRepository(db).get(user_id)
    if user is None:
        raise UnauthorizedError("Account no longer exists.", code="INVALID_TOKEN")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_roles(*roles: UserRole) -> Callable[[User], User]:
    """Dependency factory: `Depends(require_roles(UserRole.SHOP_OWNER))`."""

    def dependency(user: CurrentUser) -> User:
        if user.role not in roles:
            raise ForbiddenError()
        return user

    return dependency

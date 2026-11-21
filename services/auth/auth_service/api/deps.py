from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from auth_service.db import get_db
from auth_service.models import User
from auth_service.repositories.user_repository import UserRepository
from brewpass_common.errors import UnauthorizedError
from brewpass_common.security import CurrentPrincipal

DbSession = Annotated[Session, Depends(get_db)]


def get_current_user(principal: CurrentPrincipal, db: DbSession) -> User:
    """The auth service owns users, so it also checks the account still exists."""
    user = UserRepository(db).get(principal.user_id)
    if user is None:
        raise UnauthorizedError("Account no longer exists.", code="INVALID_TOKEN")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from auth_service.models import User
from brewpass_common.security import UserRole


class UserRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, user_id: uuid.UUID) -> User | None:
        return self.session.get(User, user_id)

    def get_by_phone(self, phone_number: str) -> User | None:
        return self.session.scalar(select(User).where(User.phone_number == phone_number))

    def create(self, phone_number: str, role: UserRole = UserRole.CUSTOMER) -> User:
        user = User(phone_number=phone_number, role=role, preferences={})
        self.session.add(user)
        self.session.flush()
        return user

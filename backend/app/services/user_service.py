from sqlalchemy.orm import Session

from app.models import User
from app.schemas.user import ProfileUpdateIn, UserOut


class UserService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def update_profile(self, user: User, data: ProfileUpdateIn) -> UserOut:
        changes = data.model_dump(exclude_unset=True)
        if "full_name" in changes:
            user.full_name = data.full_name
        if "email" in changes:
            user.email = str(data.email) if data.email else None
        if "preferences" in changes and data.preferences is not None:
            # Assign a new dict so SQLAlchemy detects the JSONB change.
            user.preferences = data.preferences.model_dump()
        self.session.commit()
        self.session.refresh(user)
        return UserOut.from_user(user)

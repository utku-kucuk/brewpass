import uuid
from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, EmailStr, Field, StringConstraints

from auth_service.models.user import User
from brewpass_common.security import UserRole

ShortText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=50)]


class UserPreferences(BaseModel):
    favorite_drinks: list[ShortText] = Field(default_factory=list, max_length=20)
    allergens: list[ShortText] = Field(default_factory=list, max_length=20)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    phone_number: str
    full_name: str | None
    email: str | None
    role: UserRole
    preferences: UserPreferences
    profile_completed: bool
    created_at: datetime

    @classmethod
    def from_user(cls, user: User) -> "UserOut":
        return cls(
            id=user.id,
            phone_number=user.phone_number,
            full_name=user.full_name,
            email=user.email,
            role=user.role,
            preferences=UserPreferences.model_validate(user.preferences or {}),
            profile_completed=bool(user.full_name),
            created_at=user.created_at,
        )


class ProfileUpdateIn(BaseModel):
    """Partial profile update; omitted fields are left unchanged."""

    model_config = ConfigDict(extra="forbid")

    full_name: (
        Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=100)]
        | None
    ) = None
    email: EmailStr | None = None
    preferences: UserPreferences | None = None

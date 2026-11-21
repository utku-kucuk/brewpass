from typing import Annotated, Literal

from pydantic import BaseModel, StringConstraints

from app.schemas.common import PhoneNumber
from app.schemas.user import UserOut

OtpCode = Annotated[str, StringConstraints(pattern=r"^\d{4,6}$")]
RefreshTokenStr = Annotated[str, StringConstraints(min_length=20, max_length=200)]


class RegisterIn(BaseModel):
    phone_number: PhoneNumber


class RegisterOut(BaseModel):
    phone_number: str
    is_new_user: bool
    otp_expires_in: int


class VerifyOtpIn(BaseModel):
    phone_number: PhoneNumber
    code: OtpCode


class RefreshIn(BaseModel):
    refresh_token: RefreshTokenStr


class TokenOut(BaseModel):
    access_token: str
    refresh_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int


class AuthOut(TokenOut):
    user: UserOut

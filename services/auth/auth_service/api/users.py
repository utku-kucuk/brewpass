from fastapi import APIRouter

from auth_service.api.deps import CurrentUser, DbSession
from auth_service.schemas.user import ProfileUpdateIn, UserOut
from auth_service.services.user_service import UserService
from brewpass_common.responses import ApiResponse, ok

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=ApiResponse[UserOut], summary="Current user's profile")
def get_me(user: CurrentUser) -> ApiResponse[UserOut]:
    return ok(UserOut.from_user(user))


@router.patch(
    "/me",
    response_model=ApiResponse[UserOut],
    summary="Complete or update the profile",
)
def update_me(body: ProfileUpdateIn, user: CurrentUser, db: DbSession) -> ApiResponse[UserOut]:
    return ok(UserService(db).update_profile(user, body))

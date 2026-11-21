from fastapi import APIRouter, FastAPI

from auth_service.api import auth, users
from auth_service.config import get_settings
from auth_service.db import SessionLocal
from brewpass_common.app import API_PREFIX, create_service_app


def create_app() -> FastAPI:
    api = APIRouter(prefix=API_PREFIX)
    api.include_router(auth.router)
    api.include_router(users.router)

    return create_service_app(
        get_settings(),
        title="BrewPass Auth Service",
        description="Phone + one-time code sign-in, token issuing and user profiles.",
        routers=[api],
        openapi_tags=[
            {"name": "auth", "description": "Phone + one-time code sign-in and token refresh."},
            {"name": "users", "description": "The signed-in user's profile."},
        ],
        session_factory=SessionLocal,
    )


app = create_app()

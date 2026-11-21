from fastapi import FastAPI

from brewpass_common.app import create_service_app
from payment_service.config import get_settings
from payment_service.db import SessionLocal


def create_app() -> FastAPI:
    return create_service_app(
        get_settings(),
        title="BrewPass Payment Service",
        description="BrewPass Pay mock card payments.",
        routers=[],
        session_factory=SessionLocal,
    )


app = create_app()

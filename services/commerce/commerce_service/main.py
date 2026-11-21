from fastapi import FastAPI

from brewpass_common.app import create_service_app
from commerce_service.config import get_settings
from commerce_service.db import SessionLocal


def create_app() -> FastAPI:
    return create_service_app(
        get_settings(),
        title="BrewPass Commerce Service",
        description="Subscription passes, credits and orders.",
        routers=[],
        session_factory=SessionLocal,
    )


app = create_app()

from fastapi import FastAPI

from brewpass_common.app import create_service_app
from payment_service.api.routes import internal_router, public_router
from payment_service.config import get_settings
from payment_service.db import SessionLocal


def create_app() -> FastAPI:
    return create_service_app(
        get_settings(),
        title="BrewPass Payment Service",
        description="BrewPass Pay mock card payments.",
        routers=[public_router, internal_router],
        openapi_tags=[
            {"name": "payments", "description": "Payment history."},
            {"name": "internal", "description": "Service-to-service routes."},
        ],
        session_factory=SessionLocal,
    )


app = create_app()

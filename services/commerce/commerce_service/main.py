from fastapi import FastAPI

from brewpass_common.app import create_service_app
from commerce_service.api import orders
from commerce_service.api.subscriptions import internal_router, router
from commerce_service.config import get_settings
from commerce_service.db import SessionLocal


def create_app() -> FastAPI:
    return create_service_app(
        get_settings(),
        title="BrewPass Commerce Service",
        description="Subscription passes, credits and orders.",
        routers=[router, orders.router, internal_router],
        openapi_tags=[
            {"name": "subscriptions", "description": "Monthly passes and credits."},
            {"name": "orders", "description": "Drink orders, status updates and QR pickup."},
            {"name": "internal", "description": "Service-to-service routes."},
        ],
        session_factory=SessionLocal,
    )


app = create_app()

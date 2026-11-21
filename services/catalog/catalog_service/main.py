from fastapi import FastAPI

from brewpass_common.app import create_service_app
from catalog_service.api import internal, shops
from catalog_service.config import get_settings
from catalog_service.db import SessionLocal


def create_app() -> FastAPI:
    return create_service_app(
        get_settings(),
        title="BrewPass Catalog Service",
        description="Partner shops, opening hours, menus and location search.",
        routers=[shops.router, internal.router],
        openapi_tags=[
            {"name": "shops", "description": "Partner shops, opening hours and menus."},
            {"name": "internal", "description": "Service-to-service routes."},
        ],
        session_factory=SessionLocal,
    )


app = create_app()

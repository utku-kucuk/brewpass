from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.errors import register_exception_handlers
from app.core.logging import configure_logging
from app.core.middleware import RequestContextMiddleware
from app.core.rate_limit import setup_rate_limiting

API_PREFIX = "/api/v1"

OPENAPI_TAGS = [
    {"name": "system", "description": "Health and service information."},
    {"name": "auth", "description": "Phone + one-time code sign-in and token refresh."},
    {"name": "users", "description": "The signed-in user's profile."},
]


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level, settings.log_format)

    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        description="REST API for BrewPass, the location-based coffee subscription platform.",
        docs_url=f"{API_PREFIX}/docs",
        redoc_url=f"{API_PREFIX}/redoc",
        openapi_url=f"{API_PREFIX}/openapi.json",
        openapi_tags=OPENAPI_TAGS,
    )

    register_exception_handlers(app)
    setup_rate_limiting(app)

    # Middleware runs outermost-last: CORS wraps everything, so even errors carry CORS headers.
    app.add_middleware(RequestContextMiddleware, hsts=settings.is_production)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
        expose_headers=["X-Request-ID"],
    )

    app.include_router(api_router)
    return app


app = create_app()

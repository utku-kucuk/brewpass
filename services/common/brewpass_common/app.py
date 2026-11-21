"""Builds a FastAPI app with the cross-cutting behaviour every BrewPass service shares."""

import logging
from collections.abc import Callable, Sequence
from typing import Any, Literal

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from brewpass_common.config import ServiceSettings
from brewpass_common.errors import register_exception_handlers
from brewpass_common.logging import configure_logging
from brewpass_common.middleware import RequestContextMiddleware
from brewpass_common.rate_limit import setup_rate_limiting
from brewpass_common.responses import ApiResponse, ok
from brewpass_common.security import get_settings_dependency

API_PREFIX = "/api/v1"
logger = logging.getLogger(__name__)


class HealthOut(BaseModel):
    service: str
    status: Literal["ok", "degraded"]
    environment: str
    database: Literal["ok", "unavailable", "not_configured"]


def _health_router(
    settings: ServiceSettings, session_factory: Callable[[], Session] | None
) -> APIRouter:
    router = APIRouter(tags=["system"])

    @router.get("/health", response_model=ApiResponse[HealthOut], summary="Service health")
    def health() -> ApiResponse[HealthOut]:
        database: Literal["ok", "unavailable", "not_configured"] = "not_configured"
        if session_factory is not None:
            try:
                with session_factory() as session:
                    session.execute(text("SELECT 1"))
                database = "ok"
            except SQLAlchemyError:
                logger.warning("Database health check failed", exc_info=True)
                database = "unavailable"
        return ok(
            HealthOut(
                service=settings.service_name,
                status="degraded" if database == "unavailable" else "ok",
                environment=settings.environment,
                database=database,
            )
        )

    return router


def create_service_app(
    settings: ServiceSettings,
    *,
    title: str,
    description: str,
    routers: Sequence[APIRouter],
    openapi_tags: list[dict[str, Any]] | None = None,
    session_factory: Callable[[], Session] | None = None,
) -> FastAPI:
    """Create a service app.

    - Public routes live under `/api/v1/...`; `/internal/...` routes are not exposed by the gateway.
    - `/health` reports service and database status.
    - Docs are served at `/api/v1/docs/<service>` so the gateway can route them per service.
    """
    configure_logging(settings.log_level, settings.log_format)
    docs_base = f"{API_PREFIX}/docs/{settings.service_name}"

    app = FastAPI(
        title=title,
        version="0.1.0",
        description=description,
        docs_url=docs_base,
        redoc_url=f"{docs_base}/redoc",
        openapi_url=f"{docs_base}/openapi.json",
        openapi_tags=[{"name": "system", "description": "Health."}, *(openapi_tags or [])],
    )
    app.dependency_overrides[get_settings_dependency] = lambda: settings

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

    app.include_router(_health_router(settings, session_factory))
    for router in routers:
        app.include_router(router)
    return app

import logging
from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.api.deps import DbSession
from app.core.config import get_settings
from app.core.responses import ApiResponse, ok

router = APIRouter(tags=["system"])
logger = logging.getLogger(__name__)


class HealthOut(BaseModel):
    status: Literal["ok", "degraded"]
    environment: str
    database: Literal["ok", "unavailable"]


@router.get("/health", response_model=ApiResponse[HealthOut], summary="Service health")
def health(db: DbSession) -> ApiResponse[HealthOut]:
    try:
        db.execute(text("SELECT 1"))
        database: Literal["ok", "unavailable"] = "ok"
    except SQLAlchemyError:
        logger.warning("Database health check failed", exc_info=True)
        database = "unavailable"

    return ok(
        HealthOut(
            status="ok" if database == "ok" else "degraded",
            environment=get_settings().environment,
            database=database,
        )
    )

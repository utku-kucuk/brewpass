"""Per-IP rate limiting (slowapi, in-memory storage).

Every route gets the default limit from settings; sensitive routes (e.g. OTP) can add a stricter
one with `@limiter.limit("5/minute")` (the route must accept a `request: Request` argument).
"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

from app.core.config import get_settings
from app.core.responses import error_payload

_settings = get_settings()

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[_settings.rate_limit_default],
    enabled=_settings.rate_limit_enabled,
)


async def _rate_limit_handler(_: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, RateLimitExceeded)
    return JSONResponse(
        status_code=429,
        content=error_payload(
            "RATE_LIMITED", "Too many requests. Please slow down.", {"limit": str(exc.detail)}
        ),
    )


def setup_rate_limiting(app: FastAPI) -> None:
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_handler)
    app.add_middleware(SlowAPIMiddleware)

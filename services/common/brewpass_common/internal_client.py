"""HTTP client for service-to-service calls on `/internal` routes.

Responses use the standard envelope; errors from the remote service are re-raised as `AppError`s
with the same code and status, and network problems become `ServiceUnavailableError`.
"""

import logging
from typing import Any

import httpx

from brewpass_common.errors import AppError, ServiceUnavailableError

logger = logging.getLogger(__name__)


class InternalClient:
    def __init__(
        self,
        base_url: str,
        internal_token: str,
        *,
        timeout: float = 5.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._client = httpx.Client(
            base_url=base_url,
            headers={"X-Internal-Token": internal_token},
            timeout=timeout,
            transport=transport,
        )

    def request(self, method: str, path: str, **kwargs: Any) -> Any:
        try:
            response = self._client.request(method, path, **kwargs)
        except httpx.HTTPError as exc:
            logger.warning(
                "Internal call failed",
                extra={"target": str(self._client.base_url), "path": path, "error": str(exc)},
            )
            raise ServiceUnavailableError() from exc

        try:
            body = response.json()
        except ValueError as exc:
            raise ServiceUnavailableError() from exc

        if response.is_success and body.get("success"):
            return body.get("data")

        error = body.get("error") or {}
        exc = AppError(
            error.get("message"),
            code=error.get("code", "UPSTREAM_ERROR"),
            details=error.get("details"),
        )
        exc.status_code = response.status_code
        raise exc

    def get(self, path: str, **kwargs: Any) -> Any:
        return self.request("GET", path, **kwargs)

    def post(self, path: str, **kwargs: Any) -> Any:
        return self.request("POST", path, **kwargs)

    def close(self) -> None:
        self._client.close()

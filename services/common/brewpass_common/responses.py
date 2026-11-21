"""Standard response envelope: `{ "success": bool, "data": ..., "error": ... }`."""

from typing import Any

from pydantic import BaseModel


class ErrorBody(BaseModel):
    code: str
    message: str
    details: Any | None = None


class ApiResponse[T](BaseModel):
    success: bool
    data: T | None = None
    error: ErrorBody | None = None


def ok[T](data: T) -> ApiResponse[T]:
    return ApiResponse[T](success=True, data=data)


def error_payload(code: str, message: str, details: Any | None = None) -> dict[str, Any]:
    body = ApiResponse[None](
        success=False, error=ErrorBody(code=code, message=message, details=details)
    )
    return body.model_dump(mode="json")

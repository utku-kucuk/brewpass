from collections.abc import Iterator

import pytest
from fastapi import APIRouter, Request
from fastapi.testclient import TestClient
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.errors import ConflictError
from app.core.rate_limit import limiter
from app.db.session import get_db
from app.main import create_app


class EchoIn(BaseModel):
    name: str
    quantity: int


# Defined once: slowapi registers a route's limit every time the decorator runs.
test_router = APIRouter(prefix="/api/v1/_test")


@test_router.post("/echo")
def echo(body: EchoIn) -> EchoIn:
    return body


@test_router.get("/conflict")
def conflict() -> None:
    raise ConflictError("Already exists.", details={"field": "phone_number"})


@test_router.get("/boom")
def boom() -> None:
    raise RuntimeError("unexpected")


@test_router.get("/limited")
@limiter.limit("2/minute")
def limited(request: Request) -> dict[str, bool]:
    return {"ok": True}


@pytest.fixture
def test_client(db_session: Session) -> Iterator[TestClient]:
    app = create_app()
    app.include_router(test_router)
    app.dependency_overrides[get_db] = lambda: db_session
    with TestClient(app, raise_server_exceptions=False) as client:
        yield client


def test_health_uses_envelope_and_checks_database(client: TestClient) -> None:
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {
        "success": True,
        "data": {"status": "ok", "environment": "test", "database": "ok"},
        "error": None,
    }


def test_unknown_route_returns_not_found_envelope(client: TestClient) -> None:
    response = client.get("/api/v1/does-not-exist")

    assert response.status_code == 404
    body = response.json()
    assert body["success"] is False
    assert body["data"] is None
    assert body["error"]["code"] == "NOT_FOUND"


def test_validation_errors_list_invalid_fields(test_client: TestClient) -> None:
    response = test_client.post("/api/v1/_test/echo", json={"name": "Flat White"})

    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "VALIDATION_ERROR"
    assert error["details"][0]["field"] == "quantity"


def test_app_errors_map_to_status_and_code(test_client: TestClient) -> None:
    response = test_client.get("/api/v1/_test/conflict")

    assert response.status_code == 409
    assert response.json()["error"] == {
        "code": "CONFLICT",
        "message": "Already exists.",
        "details": {"field": "phone_number"},
    }


def test_unexpected_errors_are_hidden_behind_generic_message(test_client: TestClient) -> None:
    response = test_client.get("/api/v1/_test/boom")

    assert response.status_code == 500
    assert response.json()["error"]["code"] == "INTERNAL_ERROR"
    assert "unexpected" not in response.text


def test_security_and_request_id_headers(client: TestClient) -> None:
    response = client.get("/api/v1/health", headers={"X-Request-ID": "abc123"})

    assert response.headers["X-Request-ID"] == "abc123"
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"


def test_cors_allows_configured_frontend_origin(client: TestClient) -> None:
    response = client.options(
        "/api/v1/health",
        headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "GET"},
    )

    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"


def test_rate_limit_returns_429_envelope(test_client: TestClient) -> None:
    limiter.enabled = True
    limiter.reset()
    try:
        statuses = [test_client.get("/api/v1/_test/limited").status_code for _ in range(3)]
        response = test_client.get("/api/v1/_test/limited")
    finally:
        limiter.enabled = False
        limiter.reset()

    assert statuses == [200, 200, 429]
    assert response.json()["error"]["code"] == "RATE_LIMITED"


def test_openapi_schema_is_served(client: TestClient) -> None:
    response = client.get("/api/v1/openapi.json")

    assert response.status_code == 200
    assert "/api/v1/health" in response.json()["paths"]

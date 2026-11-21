import httpx
import pytest
import respx

from brewpass_common.errors import AppError, ServiceUnavailableError
from brewpass_common.internal_client import InternalClient

BASE = "http://catalog:8000"


@pytest.fixture
def client() -> InternalClient:
    return InternalClient(BASE, "token-123")


@respx.mock
def test_returns_data_and_sends_internal_token(client: InternalClient) -> None:
    route = respx.get(f"{BASE}/internal/products/1").mock(
        return_value=httpx.Response(200, json={"success": True, "data": {"id": 1}, "error": None})
    )

    assert client.get("/internal/products/1") == {"id": 1}
    assert route.calls.last.request.headers["X-Internal-Token"] == "token-123"


@respx.mock
def test_remote_errors_keep_code_and_status(client: InternalClient) -> None:
    respx.get(f"{BASE}/internal/products/2").mock(
        return_value=httpx.Response(
            404,
            json={
                "success": False,
                "data": None,
                "error": {
                    "code": "PRODUCT_NOT_FOUND",
                    "message": "No such drink.",
                    "details": None,
                },
            },
        )
    )

    with pytest.raises(AppError) as exc_info:
        client.get("/internal/products/2")

    assert exc_info.value.status_code == 404
    assert exc_info.value.code == "PRODUCT_NOT_FOUND"


@respx.mock
def test_network_errors_become_service_unavailable(client: InternalClient) -> None:
    respx.get(f"{BASE}/internal/products/3").mock(side_effect=httpx.ConnectError("refused"))

    with pytest.raises(ServiceUnavailableError):
        client.get("/internal/products/3")


@respx.mock
def test_non_json_responses_become_service_unavailable(client: InternalClient) -> None:
    respx.get(f"{BASE}/internal/products/4").mock(return_value=httpx.Response(502, text="Bad"))

    with pytest.raises(ServiceUnavailableError):
        client.get("/internal/products/4")

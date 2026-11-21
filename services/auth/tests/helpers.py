from typing import Any

from fastapi.testclient import TestClient

from auth_service.config import get_settings

CUSTOMER_PHONE = "+905321112233"


def sign_in(client: TestClient, phone_number: str = CUSTOMER_PHONE) -> dict[str, Any]:
    """Run the full OTP flow and return the `data` of the verify-otp response."""
    assert client.post("/api/v1/auth/register", json={"phone_number": phone_number}).is_success
    response = client.post(
        "/api/v1/auth/verify-otp",
        json={"phone_number": phone_number, "code": get_settings().otp_mock_code},
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]


def auth_header(access_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {access_token}"}

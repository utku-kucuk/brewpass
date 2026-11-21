from fastapi.testclient import TestClient

from tests.helpers import auth_header, sign_in

ME = "/api/v1/users/me"


def test_get_me_returns_profile(client: TestClient) -> None:
    token = sign_in(client)["access_token"]

    response = client.get(ME, headers=auth_header(token))

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["role"] == "CUSTOMER"
    assert data["preferences"] == {"favorite_drinks": [], "allergens": []}


def test_profile_completion(client: TestClient) -> None:
    token = sign_in(client)["access_token"]

    response = client.patch(
        ME,
        headers=auth_header(token),
        json={
            "full_name": "  Zeynep Arslan ",
            "email": "zeynep@example.com",
            "preferences": {"favorite_drinks": ["Flat White"], "allergens": ["lactose"]},
        },
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["full_name"] == "Zeynep Arslan"
    assert data["email"] == "zeynep@example.com"
    assert data["preferences"]["allergens"] == ["lactose"]
    assert data["profile_completed"] is True


def test_partial_update_keeps_other_fields(client: TestClient) -> None:
    token = sign_in(client)["access_token"]
    client.patch(ME, headers=auth_header(token), json={"full_name": "Zeynep Arslan"})

    response = client.patch(ME, headers=auth_header(token), json={"email": "z@example.com"})

    assert response.json()["data"]["full_name"] == "Zeynep Arslan"


def test_profile_validation_errors(client: TestClient) -> None:
    token = sign_in(client)["access_token"]

    response = client.patch(
        ME, headers=auth_header(token), json={"full_name": "Z", "email": "not-an-email"}
    )

    assert response.status_code == 422
    fields = {d["field"] for d in response.json()["error"]["details"]}
    assert fields == {"full_name", "email"}


def test_role_cannot_be_changed_through_profile(client: TestClient) -> None:
    token = sign_in(client)["access_token"]

    response = client.patch(ME, headers=auth_header(token), json={"role": "ADMIN"})

    assert response.status_code == 422

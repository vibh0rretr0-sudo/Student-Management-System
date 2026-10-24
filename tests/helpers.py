"""Shared HTTP helpers for the API tests."""
from __future__ import annotations

DEMO_PASSWORD = "Jecrc@2026"


def get_csrf(client) -> str:
    response = client.get("/api/auth/csrf")
    assert response.status_code == 200, response.get_data(as_text=True)
    return response.get_json()["data"]["csrf_token"]


def login(client, identifier: str, role: str = "student",
          password: str = DEMO_PASSWORD, remember: bool = False):
    token = get_csrf(client)
    return client.post(
        "/api/auth/login",
        json={"role": role, "identifier": identifier, "password": password,
              "remember": remember},
        headers={"X-CSRF-Token": token},
    )


def auth_headers(client) -> dict:
    return {"X-CSRF-Token": get_csrf(client)}


def student_login(client, roll: str = "26csai001"):
    response = login(client, roll, "student")
    assert response.status_code == 200, response.get_data(as_text=True)
    return response


def professor_login(client, username: str = "rakesh.sharma"):
    response = login(client, username, "professor")
    assert response.status_code == 200, response.get_data(as_text=True)
    return response

from datetime import datetime

import pytest

from helpers import get_csrf, login, professor_login, student_login


def test_student_login_sets_secure_session_cookie(client):
    response = student_login(client)
    payload = response.get_json()
    assert payload["ok"] is True
    assert payload["data"]["user"]["role"] == "student"
    cookies = response.headers.getlist("Set-Cookie")
    session_cookie = next(c for c in cookies if c.startswith("jecrc_session="))
    assert "HttpOnly" in session_cookie
    assert "SameSite=Lax" in session_cookie

    session = client.get("/api/auth/session").get_json()["data"]
    assert session["authenticated"] is True
    assert session["user"]["name"]
    assert session["csrf_token"]


def test_professor_login(client):
    response = professor_login(client)
    assert response.status_code == 200
    user = response.get_json()["data"]["user"]
    assert user["role"] == "professor"
    assert user["department"]


def test_wrong_password_is_generic(client):
    response = login(client, "26csai001", "student", password="wrong-password")
    assert response.status_code == 401
    message = response.get_json()["error"]["message"].lower()
    assert "password" in message
    assert "roll number" in message  # generic wording covers both fields
    assert "does not exist" not in message


def test_wrong_role_is_indistinguishable(client):
    response = login(client, "26csai001", "professor", password="Jecrc@2026")
    assert response.status_code == 401
    assert response.get_json()["error"]["code"] == "invalid_credentials"


def test_login_requires_csrf(client):
    response = client.post("/api/auth/login", json={
        "role": "student", "identifier": "26csai001",
        "password": "Jecrc@2026",
    })
    assert response.status_code == 403
    assert response.get_json()["error"]["code"] == "csrf_invalid"


def test_rate_limit_locks_after_repeated_failures(client):
    token = get_csrf(client)
    headers = {"X-CSRF-Token": token}
    for _ in range(5):
        response = client.post("/api/auth/login", json={
            "role": "student", "identifier": "26csai001",
            "password": "bad-password",
        }, headers=headers)
        assert response.status_code == 401
    locked = client.post("/api/auth/login", json={
        "role": "student", "identifier": "26csai001",
        "password": "Jecrc@2026",
    }, headers=headers)
    assert locked.status_code == 429
    assert locked.get_json()["error"]["code"] == "locked"


def test_logout_invalidates_session(client):
    student_login(client)
    token = get_csrf(client)
    response = client.post("/api/auth/logout", headers={"X-CSRF-Token": token})
    assert response.status_code == 200
    after = client.get("/api/student/overview")
    assert after.status_code == 401


def test_validation_errors_are_field_level(client):
    token = get_csrf(client)
    response = client.post("/api/auth/login", json={
        "role": "student", "identifier": "", "password": "",
    }, headers={"X-CSRF-Token": token})
    assert response.status_code == 422
    assert "identifier" in response.get_json()["error"]["fields"]


def test_mobile_user_agent_gets_blocked_page(client):
    response = client.get(
        "/", headers={"User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0)"}
    )
    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert "This portal is accessible only from a laptop or desktop." in body


def test_security_headers_present(client):
    response = client.get("/")
    assert response.status_code == 200
    csp = response.headers["Content-Security-Policy"]
    assert "default-src 'self'" in csp
    assert "frame-ancestors 'none'" in csp
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"]


def test_remember_me_extends_cookie_lifetime(client):
    response = login(client, "26csai001", "student", remember=True)
    assert response.status_code == 200
    cookie = next(c for c in response.headers.getlist("Set-Cookie")
                  if c.startswith("jecrc_session="))
    assert "Expires=" in cookie or "Max-Age=" in cookie


def test_session_expiry_enforced(app, client):
    student_login(client)
    token = client.get("/api/auth/csrf").get_json()["data"]["csrf_token"]
    from app.db import db_from_config

    database = db_from_config(app.config)
    try:
        stale = datetime(2020, 1, 1, 0, 0, 0).strftime("%Y-%m-%d %H:%M:%S")
        database.execute("UPDATE sessions SET last_seen = ?, expires_at = ?",
                         (stale, stale))
    finally:
        database.close()
    response = client.get("/api/student/overview")
    assert response.status_code == 401
    assert token


def test_campus_images_listed_and_cached(client):
    first = client.get("/api/common/campus-images")
    assert first.status_code == 200
    images = first.get_json()["data"]["images"]
    assert len(images) >= 4
    assert first.headers["Cache-Control"].startswith("public")
    assert all(item["url"].startswith("/static/img/campus/") for item in images)

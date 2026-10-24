"""Authentication: CSRF bootstrap, login, logout, session, heartbeat."""
from __future__ import annotations

from flask import Blueprint, current_app, request

from ..db import get_db
from ..security import (
    clear_session,
    clear_session_cookie,
    create_session,
    ensure_anonymous_session,
    load_profile,
    login_lock_minutes,
    record_login_attempt,
    session_row,
    set_session_cookie,
    verify_password,
)
from ..utils import audit, body, client_ip, iso, json_err, json_ok, now

bp = Blueprint("auth", __name__, url_prefix="/api/auth")


def _profile_payload(profile: dict) -> dict:
    payload = {
        "user_id": profile["user_id"],
        "role": profile["role"],
        "name": profile["name"],
        "photo": profile.get("photo"),
        "email": profile.get("email"),
    }
    if profile["role"] == "student":
        payload.update({
            "roll_no": profile["roll_no"],
            "batch": profile["batch"],
            "batch_code": profile["batch_code"],
            "branch": profile["branch"],
            "semester": profile["semester"],
        })
    else:
        payload.update({
            "employee_id": profile["employee_id"],
            "department": profile["department"],
            "designation": profile["designation"],
        })
    return payload


@bp.get("/csrf")
def csrf():
    row = ensure_anonymous_session()
    response = json_ok({"csrf_token": row["csrf_token"]})
    set_session_cookie(response, row["token"],
                       bool(row.get("remember")))
    response.headers["Cache-Control"] = "no-store"
    return response


@bp.post("/login")
def login():
    data = body()
    role = str(data.get("role", "")).strip().lower()
    identifier = str(data.get("identifier", "")).strip().lower()
    password = str(data.get("password", ""))
    remember = bool(data.get("remember"))

    fields = {}
    if role not in ("student", "professor"):
        fields["role"] = "Choose whether you are a student or a professor."
    if not identifier:
        fields["identifier"] = "Enter your roll number or username."
    elif len(identifier) > 80:
        fields["identifier"] = "That identifier is too long."
    if not password:
        fields["password"] = "Enter your password."
    if fields:
        return json_err("Please fix the highlighted fields.", 422, "validation",
                        fields=fields)

    ip = client_ip()
    locked_for = login_lock_minutes(identifier, ip)
    if locked_for:
        return json_err(
            f"Too many failed attempts. Try again in about {locked_for} minute"
            f"{'s' if locked_for != 1 else ''}.",
            429, "locked", retry_after_minutes=locked_for,
        )

    db = get_db()
    user = db.query_one(
        "SELECT * FROM users WHERE username = ? AND role = ?",
        (identifier, role),
    )
    authenticated = bool(
        user and user["is_active"] and verify_password(user["password_hash"], password)
    )
    record_login_attempt(identifier, ip, authenticated)

    if not authenticated:
        audit("login_failed", "user", None, f"role={role}")
        return json_err(
            "Those details don't match our records. Check your "
            + ("roll number" if role == "student" else "username")
            + " and password, then try again.",
            401, "invalid_credentials",
        )

    previous = session_row()
    token = create_session(user["id"], remember=remember,
                           replace_token=previous["token"] if previous else None)
    profile = load_profile()
    audit("login", "user", user["id"], f"role={role}")

    response = json_ok({
        "user": _profile_payload(profile),
        "csrf_token": profile["csrf_token"],
        "redirect": "/app",
    })
    set_session_cookie(response, token, remember)
    response.headers["Cache-Control"] = "no-store"
    return response


@bp.post("/logout")
def logout():
    row = session_row()
    if row and row.get("user_id"):
        audit("logout", "user", row["user_id"])
    clear_session()
    response = json_ok({"message": "Signed out."})
    clear_session_cookie(response)
    response.headers["Cache-Control"] = "no-store"
    return response


@bp.get("/session")
def session_info():
    row = session_row()
    profile = load_profile() if row and row.get("user_id") else None

    if not profile:
        anonymous = ensure_anonymous_session()
        return json_ok({
            "authenticated": False,
            "csrf_token": anonymous["csrf_token"],
            "server_time": iso(now()),
        })

    response = json_ok({
        "authenticated": True,
        "user": _profile_payload(profile),
        "csrf_token": profile["csrf_token"],
        "idle_minutes": current_app.config["SESSION_IDLE_MINUTES"],
        "warn_minutes": current_app.config["SESSION_WARN_MINUTES"],
        "threshold": current_app.config["ATTENDANCE_THRESHOLD"],
        "server_time": iso(now()),
        "session_expires_at": iso(row.get("expires_at")),
    })
    response.headers["Cache-Control"] = "no-store"
    return response


@bp.post("/heartbeat")
def heartbeat():
    row = session_row()
    if not row or not row.get("user_id"):
        return json_err("Your session has ended. Please sign in again.",
                        401, "unauthenticated")
    db = get_db()
    db.execute("UPDATE sessions SET last_seen = ? WHERE token = ?",
               (now(), row["token"]))
    audit("heartbeat", "session", None, "")
    response = json_ok({
        "extended": True,
        "server_time": iso(now()),
        "idle_minutes": current_app.config["SESSION_IDLE_MINUTES"],
        "warn_minutes": current_app.config["SESSION_WARN_MINUTES"],
    })
    response.headers["Cache-Control"] = "no-store"
    return response

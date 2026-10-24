"""HTML pages: marketing-style home, dashboard shell, blocked screen."""
from __future__ import annotations

import re

from flask import Blueprint, current_app, jsonify, make_response, redirect, render_template

from ..security import (
    ensure_anonymous_session,
    is_mobile_user_agent,
    load_profile,
    set_session_cookie,
)
from ..utils import now

bp = Blueprint("pages", __name__)


def _photo_url(profile: dict) -> str:
    if not profile.get("photo"):
        return ""
    kind = "student" if profile["role"] == "student" else "professor"
    entity_id = profile.get("student_id") or profile.get("professor_id")
    return f"/api/common/avatar/{kind}/{entity_id}?v={profile['photo'][:8]}"


@bp.get("/")
def home():
    profile = load_profile()
    if profile:
        return redirect("/app")
    row = ensure_anonymous_session()
    response = make_response(render_template(
        "home.html",
        csrf_token=row["csrf_token"],
        demo_password="Jecrc@2026",
    ))
    set_session_cookie(response, row["token"])
    response.headers["Cache-Control"] = "no-store"
    return response


@bp.get("/app")
def dashboard():
    profile = load_profile()
    if not profile:
        return redirect("/")
    # Strip a leading academic honorific ("Dr." / "Prof.") so the top bar and
    # menus show "Rakesh Sharma", not "Prof. Rakesh Sharma".
    display_name = re.sub(r"^(Dr\.|Prof\.)\s*", "", profile["name"] or "").strip()
    boot = {
        "user": {
            "user_id": profile["user_id"],
            "role": profile["role"],
            "name": profile["name"],
            "display_name": display_name,
            "username": profile["username"],
            "photo_url": _photo_url(profile),
            "email": profile.get("email"),
        },
        "csrf_token": profile["csrf_token"],
        "threshold": current_app.config["ATTENDANCE_THRESHOLD"],
        "idle_minutes": current_app.config["SESSION_IDLE_MINUTES"],
        "warn_minutes": current_app.config["SESSION_WARN_MINUTES"],
        "server_time": now().isoformat(),
    }
    if profile["role"] == "student":
        boot["user"].update({
            "roll_no": profile["roll_no"], "batch": profile["batch"],
            "batch_code": profile["batch_code"], "branch": profile["branch"],
            "semester": profile["semester"],
        })
    else:
        boot["user"].update({
            "employee_id": profile["employee_id"],
            "department": profile["department"],
            "designation": profile["designation"],
        })
    response = make_response(render_template("app.html", boot=boot))
    response.headers["Cache-Control"] = "no-store"
    return response


@bp.get("/blocked")
def blocked():
    response = make_response(render_template("blocked.html"))
    response.headers["Cache-Control"] = "no-store"
    return response


@bp.get("/health")
def health():
    return jsonify({"ok": True, "service": "jecrc-portal", "time": now().isoformat()})


@bp.get("/favicon.ico")
def favicon():
    return redirect("/static/img/favicon.svg", code=302)

"""Security helpers: DB-backed sessions, CSRF, role guards, lockout, uploads."""
from __future__ import annotations

import re
import secrets
from datetime import datetime, timedelta
from functools import wraps

from flask import current_app, g, request
from werkzeug.security import check_password_hash, generate_password_hash

from .db import get_db
from .utils import json_err, now, parse_datetime

SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}
MOBILE_UA_RE = re.compile(
    r"(android|webos|iphone|ipad|ipod|blackberry|iemobile|opera mini|"
    r"windows phone|mobile|tablet|silk|kindle)",
    re.IGNORECASE,
)


# --------------------------------------------------------------------------
# Passwords
# --------------------------------------------------------------------------
def hash_password(raw: str) -> str:
    return generate_password_hash(raw)


def verify_password(password_hash: str, raw: str) -> bool:
    try:
        return check_password_hash(password_hash, raw)
    except (ValueError, TypeError):
        return False


# --------------------------------------------------------------------------
# Sessions (server-side rows + HttpOnly cookie)
# --------------------------------------------------------------------------
def _config():
    return current_app.config


def _idle_delta():
    return timedelta(minutes=_config()["SESSION_IDLE_MINUTES"])


def session_row():
    """Load the session for this request, enforcing idle + absolute expiry."""
    if "session_row" in g:
        return g.session_row
    token = request.cookies.get(_config()["SESSION_COOKIE_NAME"])
    row = None
    if token:
        db = get_db()
        row = db.query_one("SELECT * FROM sessions WHERE token = ?", (token,))
        if row:
            current = now()
            expires = parse_datetime(row.get("expires_at"))
            last_seen = parse_datetime(row.get("last_seen"))
            if expires and current > expires:
                db.execute("DELETE FROM sessions WHERE token = ?", (token,))
                row = None
            elif last_seen and current - last_seen > _idle_delta():
                db.execute("DELETE FROM sessions WHERE token = ?", (token,))
                row = None
            elif not last_seen or (current - last_seen).total_seconds() > 45:
                db.execute("UPDATE sessions SET last_seen = ? WHERE token = ?",
                           (current, token))
                row["last_seen"] = current
    g.session_row = row
    return row


def create_session(user_id: int | None, remember: bool = False,
                   replace_token: str | None = None):
    db = get_db()
    if replace_token:
        db.execute("DELETE FROM sessions WHERE token = ?", (replace_token,))
    token = secrets.token_urlsafe(48)
    csrf = secrets.token_urlsafe(32)
    current = now()
    if remember and user_id:
        expires = current + timedelta(days=_config()["SESSION_REMEMBER_DAYS"])
    else:
        expires = current + timedelta(hours=_config()["SESSION_HOURS"])
    db.insert("sessions", {
        "token": token,
        "user_id": user_id,
        "csrf_token": csrf,
        "remember": 1 if remember else 0,
        "created_at": current,
        "last_seen": current,
        "expires_at": expires,
        "ip": (request.remote_addr or "")[:45],
        "user_agent": (request.user_agent.string or "")[:255],
    })
    g.session_row = db.query_one("SELECT * FROM sessions WHERE token = ?", (token,))
    g.pop("user_profile", None)
    return token


def set_session_cookie(response, token: str, remember: bool = False):
    max_age = None
    if remember:
        max_age = _config()["SESSION_REMEMBER_DAYS"] * 24 * 3600
    response.set_cookie(
        _config()["SESSION_COOKIE_NAME"],
        token,
        max_age=max_age,
        httponly=True,
        samesite="Lax",
        secure=_config()["SESSION_COOKIE_SECURE"],
        path="/",
    )
    return response


def clear_session():
    row = session_row()
    if row:
        get_db().execute("DELETE FROM sessions WHERE token = ?", (row["token"],))
    g.session_row = None
    g.pop("user_profile", None)


def clear_session_cookie(response):
    response.delete_cookie(
        _config()["SESSION_COOKIE_NAME"],
        path="/",
        httponly=True,
        samesite="Lax",
        secure=_config()["SESSION_COOKIE_SECURE"],
    )
    return response


# --------------------------------------------------------------------------
# CSRF
# --------------------------------------------------------------------------
def ensure_anonymous_session():
    row = session_row()
    if row:
        return row
    create_session(None, remember=False)
    return g.session_row


def check_csrf():
    """Validate X-CSRF-Token for every state-changing API request."""
    if request.method in SAFE_METHODS:
        return None
    if not request.path.startswith("/api/"):
        return None
    row = session_row()
    supplied = request.headers.get("X-CSRF-Token", "")
    if not row or not supplied or not secrets.compare_digest(
        str(row.get("csrf_token") or ""), supplied
    ):
        return json_err("Your security token expired. Refresh the page and try again.",
                        403, "csrf_invalid")
    return None


# --------------------------------------------------------------------------
# Current user profile
# --------------------------------------------------------------------------
def load_profile():
    if "user_profile" in g:
        return g.user_profile
    row = session_row()
    if not row or not row.get("user_id"):
        g.user_profile = None
        return None
    db = get_db()
    user = db.query_one(
        "SELECT id, username, role, is_active FROM users WHERE id = ?",
        (row["user_id"],),
    )
    if not user or not user["is_active"]:
        g.user_profile = None
        return None

    profile = {
        "user_id": user["id"],
        "role": user["role"],
        "username": user["username"],
        "csrf_token": row["csrf_token"],
    }
    if user["role"] == "student":
        student = db.query_one(
            """SELECT s.*, b.code AS batch_code, b.name AS batch_name,
                      b.branch AS batch_branch, b.semester AS batch_semester
               FROM students s LEFT JOIN batches b ON b.id = s.batch_id
               WHERE s.user_id = ?""",
            (user["id"],),
        )
        if not student:
            g.user_profile = None
            return None
        profile.update({
            "student_id": student["id"],
            "name": student["full_name"],
            "roll_no": student["roll_no"],
            "batch_id": student["batch_id"],
            "batch": student["batch_name"],
            "batch_code": student["batch_code"],
            "branch": student["branch"] or student["batch_branch"],
            "semester": student["batch_semester"],
            "email": student["email"],
            "phone": student["phone"],
            "photo": student["photo"],
        })
    elif user["role"] == "professor":
        professor = db.query_one(
            "SELECT * FROM professors WHERE user_id = ?", (user["id"],)
        )
        if not professor:
            g.user_profile = None
            return None
        assignments = db.query(
            """SELECT pbs.batch_id, pbs.subject_id, b.code AS batch_code,
                      b.name AS batch_name, s.code AS subject_code,
                      s.name AS subject_name
               FROM professor_batch_subject pbs
               JOIN batches b ON b.id = pbs.batch_id
               JOIN subjects s ON s.id = pbs.subject_id
               WHERE pbs.professor_id = ?
               ORDER BY b.name, s.code""",
            (professor["id"],),
        )
        profile.update({
            "professor_id": professor["id"],
            "name": professor["full_name"],
            "employee_id": professor["employee_id"],
            "department": professor["department"],
            "designation": professor["designation"],
            "qualifications": professor["qualifications"],
            "email": professor["email"],
            "phone": professor["phone"],
            "photo": professor["photo"],
            "teachings": assignments,
        })
    g.user_profile = profile
    return profile


def current_user():
    return load_profile()


# --------------------------------------------------------------------------
# Decorators
# --------------------------------------------------------------------------
def api_login_required(fn):
    """Any signed-in role.  CSRF is enforced globally for unsafe API calls."""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        profile = load_profile()
        if not profile:
            return json_err("Please sign in to continue.", 401, "unauthenticated")
        g.user = profile
        return fn(*args, **kwargs)

    return wrapper


def role_required(role: str):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            profile = load_profile()
            if not profile:
                return json_err("Please sign in to continue.", 401, "unauthenticated")
            if profile["role"] != role:
                return json_err("You do not have access to this area.", 403,
                                "forbidden")
            g.user = profile
            return fn(*args, **kwargs)

        return wrapper

    return decorator


student_required = role_required("student")
professor_required = role_required("professor")


# --------------------------------------------------------------------------
# Login rate limiting
# --------------------------------------------------------------------------
def login_lock_minutes(identifier: str, ip: str) -> int:
    db = get_db()
    window = now() - timedelta(minutes=_config()["LOGIN_WINDOW_MINUTES"])
    last = db.query_one(
        """SELECT attempted_at FROM login_attempts
           WHERE identifier = ? AND ip = ? AND success = 0
           ORDER BY attempted_at DESC LIMIT 1""",
        (identifier, ip),
    )
    count = db.scalar(
        """SELECT COUNT(*) AS c FROM login_attempts
           WHERE identifier = ? AND ip = ? AND success = 0
             AND attempted_at >= ?""",
        (identifier, ip, window),
        default=0,
    )
    if count >= _config()["LOGIN_MAX_ATTEMPTS"] and last:
        last_at = parse_datetime(last["attempted_at"])
        unlock = last_at + timedelta(minutes=_config()["LOGIN_LOCK_MINUTES"])
        remaining = (unlock - now()).total_seconds()
        if remaining > 0:
            return max(1, int(remaining // 60) + 1)
    return 0


def record_login_attempt(identifier: str, ip: str, success: bool):
    db = get_db()
    db.insert("login_attempts", {
        "identifier": identifier[:120],
        "ip": ip[:45],
        "success": 1 if success else 0,
        "attempted_at": now(),
    })
    if success:
        db.execute(
            "DELETE FROM login_attempts WHERE identifier = ? AND ip = ? AND success = 0",
            (identifier[:120], ip[:45]),
        )


# --------------------------------------------------------------------------
# Device detection
# --------------------------------------------------------------------------
def is_mobile_user_agent(ua: str | None = None) -> bool:
    agent = ua if ua is not None else (request.user_agent.string or "")
    return bool(MOBILE_UA_RE.search(agent or ""))

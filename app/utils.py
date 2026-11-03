"""Shared helpers: JSON envelope, validation, dates, uploads, audit, notify."""
from __future__ import annotations

import re
import uuid
from datetime import date, datetime, timedelta
from pathlib import Path

from flask import current_app, g, jsonify, request
from werkzeug.utils import secure_filename

from .db import get_db

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[A-Za-z]{2,}$")
PHONE_RE = re.compile(r"^[0-9+\-\s()]{7,18}$")


# --------------------------------------------------------------------------
# JSON envelope
# --------------------------------------------------------------------------
def json_ok(data=None, status: int = 200, meta=None):
    payload = {"ok": True, "data": data, "error": None}
    if meta is not None:
        payload["meta"] = meta
    response = jsonify(payload)
    response.status_code = status
    return response


def json_err(message: str, status: int = 400, code: str | None = None,
             fields: dict | None = None, **extra):
    error = {"message": message}
    if code:
        error["code"] = code
    if fields:
        error["fields"] = fields
    error.update(extra)
    response = jsonify({"ok": False, "data": None, "error": error})
    response.status_code = status
    return response


def body() -> dict:
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else {}


def iso(value):
    """Serialize date/datetime/time values from either engine."""
    if value is None:
        return None
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    text = str(value)
    if re.fullmatch(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}", text):
        return text.replace(" ", "T")
    if re.fullmatch(r"\d{2}:\d{2}:\d{2}", text):
        return text[:5]
    return text


def hhmm(value) -> str:
    """Format TIME values from either engine (MySQL returns timedelta)."""
    if isinstance(value, timedelta):
        total = int(value.total_seconds())
        return f"{total // 3600:02d}:{(total % 3600) // 60:02d}"
    text = str(value)
    if len(text) >= 5 and text[2:3] == ":":
        return text[:5]
    if len(text) >= 8 and text[1:2] == ":":
        return "0" + text[:4]
    return text[:5]


def now() -> datetime:
    return datetime.now()


def parse_date(value, default=None):
    if not value:
        return default
    try:
        return datetime.strptime(str(value)[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


def parse_datetime(value, default=None):
    if not value:
        return default
    text = str(value).replace("T", " ")
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    return None


def valid_email(value) -> bool:
    return bool(value) and bool(EMAIL_RE.fullmatch(str(value).strip()))


def valid_phone(value) -> bool:
    text = str(value).strip() if value else ""
    return (
        bool(text)
        and bool(PHONE_RE.fullmatch(text))
        and 7 <= sum(char.isdigit() for char in text) <= 15
    )


def paginate(default_per: int = 20, max_per: int = 100):
    try:
        page = max(1, int(request.args.get("page", 1)))
    except (TypeError, ValueError):
        page = 1
    try:
        per = min(max_per, max(1, int(request.args.get("per_page", default_per))))
    except (TypeError, ValueError):
        per = default_per
    return page, per, (page - 1) * per


def page_meta(page: int, per: int, total: int) -> dict:
    return {
        "page": page,
        "per_page": per,
        "total": total,
        "pages": max(1, (total + per - 1) // per),
    }


# --------------------------------------------------------------------------
# Audit / notifications
# --------------------------------------------------------------------------
def client_ip() -> str:
    return (request.remote_addr or "")[:45]


def audit(action: str, entity: str = "", entity_id=None, meta: str = ""):
    try:
        sess = getattr(g, "user", None) or getattr(g, "session", None) or {}
        get_db().insert("audit_log", {
            "user_id": sess.get("user_id"),
            "action": action,
            "entity": entity,
            "entity_id": str(entity_id) if entity_id is not None else None,
            "meta": meta[:2000],
            "ip": client_ip(),
            "created_at": now(),
        })
    except Exception:  # auditing must never break a request
        current_app.logger.exception("audit write failed")


def notify(user_id: int, title: str, message: str, link: str = "",
           kind: str = "info"):
    get_db().insert("notifications", {
        "user_id": user_id,
        "title": title,
        "body": message,
        "link": link,
        "kind": kind,
        "is_read": 0,
        "created_at": now(),
    })


# --------------------------------------------------------------------------
# Uploads
# --------------------------------------------------------------------------
def save_upload(file_storage, allowed: set[str] | None = None) -> dict | None:
    """Validate + store an upload with a randomized filename."""
    if not file_storage or not file_storage.filename:
        return None
    original = secure_filename(file_storage.filename)
    if not original or "." not in original:
        raise ValueError("That file has no extension.")
    ext = original.rsplit(".", 1)[1].lower()
    allowed = allowed or current_app.config["ALLOWED_UPLOAD_EXTENSIONS"]
    if ext not in allowed:
        raise ValueError(
            "Unsupported file type. Allowed: " + ", ".join(sorted(allowed)).upper() + "."
        )

    upload_dir = Path(current_app.config["UPLOAD_DIR"])
    upload_dir.mkdir(parents=True, exist_ok=True)
    stored = f"{uuid.uuid4().hex}.{ext}"
    target = upload_dir / stored
    file_storage.save(target)
    size = target.stat().st_size
    if size == 0:
        target.unlink(missing_ok=True)
        raise ValueError("The uploaded file is empty.")
    if size > current_app.config["MAX_CONTENT_LENGTH"]:
        target.unlink(missing_ok=True)
        max_mb = current_app.config["MAX_CONTENT_LENGTH"] / (1024 * 1024)
        raise ValueError(f"File is larger than the {max_mb:g} MB limit.")
    return {
        "stored": stored,
        "name": original[:180],
        "size": size,
        "ext": ext,
    }


def delete_upload(stored: str):
    if not stored:
        return
    path = Path(current_app.config["UPLOAD_DIR"]) / Path(stored).name
    try:
        path.unlink(missing_ok=True)
    except OSError:
        pass


def delete_upload_if_unreferenced(stored: str, *, kind: str, entity_id: int):
    """Delete an upload only when no remaining record points at it."""
    if not stored:
        return
    db = get_db()
    if kind == "submission":
        row = db.query_one(
            """SELECT 1 FROM submissions WHERE file_path = ? AND id <> ?
               UNION ALL
               SELECT 1 FROM assignments WHERE attachment_path = ? LIMIT 1""",
            (stored, entity_id, stored),
        )
    elif kind == "assignment":
        row = db.query_one(
            """SELECT 1 FROM assignments WHERE attachment_path = ? AND id <> ?
               UNION ALL
               SELECT 1 FROM submissions WHERE file_path = ? LIMIT 1""",
            (stored, entity_id, stored),
        )
    else:
        raise ValueError(f"Unknown upload reference kind: {kind}")
    if not row:
        delete_upload(stored)


def human_size(size) -> str:
    size = int(size or 0)
    for unit in ("B", "KB", "MB"):
        if size < 1024 or unit == "MB":
            return f"{size:.0f} {unit}" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} MB"


# --------------------------------------------------------------------------
# Attendance calculation
# --------------------------------------------------------------------------
def attendance_stats(attended: int, held: int, threshold: int = 75) -> dict:
    attended, held = int(attended or 0), int(held or 0)
    percentage = round((attended * 100.0 / held), 1) if held else 0.0
    can_miss = 0
    need_attend = 0
    if held:
        if percentage >= threshold:
            # Future classes x keep you at/above the threshold:
            # attended / (held + x) >= t  =>  x <= attended/t - held
            can_miss = max(0, int(attended / (threshold / 100.0)) - held)
        else:
            # Classes y you must attend: (attended+y)/(held+y) >= t
            need_attend = 0
            while (attended + need_attend) * 100.0 / (held + need_attend) < threshold:
                need_attend += 1
    return {
        "attended": attended,
        "held": held,
        "percentage": percentage,
        "can_miss": can_miss,
        "need_attend": need_attend,
        "below_threshold": held > 0 and percentage < threshold,
        "threshold": threshold,
    }

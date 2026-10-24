"""Shared endpoints: profile, notifications, command-palette search, files."""
from __future__ import annotations

import time
from pathlib import Path

from flask import Blueprint, current_app, g, request, send_file

from ..db import get_db
from ..security import api_login_required, hash_password, verify_password
from ..utils import (
    audit,
    body,
    delete_upload,
    iso,
    json_err,
    json_ok,
    now,
    page_meta,
    paginate,
    save_upload,
    valid_email,
    valid_phone,
)

bp = Blueprint("common", __name__, url_prefix="/api/common")

PAGES = {
    "student": [
        ("Overview", "Dashboard summary, attendance, schedule", "/#/overview"),
        ("Attendance", "Subject-wise attendance and trend", "/#/attendance"),
        ("Timetable", "Weekly class grid", "/#/timetable"),
        ("Assignments", "Submit work and read remarks", "/#/assignments"),
        ("Announcements", "Notices from faculty", "/#/announcements"),
        ("Today's Schedule", "Timeline for today", "/#/schedule"),
        ("Personal Details", "Profile and contact details", "/#/profile"),
    ],
    "professor": [
        ("Overview", "Dashboard summary and alerts", "/#/overview"),
        ("My Batches", "Batches, subjects and students", "/#/batches"),
        ("Attendance", "Mark and review attendance", "/#/attendance"),
        ("Assignments", "Create, review and grade", "/#/assignments"),
        ("Announcements", "Post and manage notices", "/#/announcements"),
        ("Today's Schedule", "Your teaching timeline", "/#/schedule"),
        ("Personal Details", "Profile and contact details", "/#/profile"),
    ],
}

CAMPUS_CACHE: dict = {"mtime": 0, "items": []}
CAMPUS_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".svg"}


def _photo_url(profile: dict) -> str:
    if not profile.get("photo"):
        return ""
    kind = "student" if profile["role"] == "student" else "professor"
    entity_id = profile.get("student_id") or profile.get("professor_id")
    return f"/api/common/avatar/{kind}/{entity_id}?v={profile['photo'][:8]}"


def detailed_profile(profile: dict) -> dict:
    db = get_db()
    base = {
        "role": profile["role"],
        "name": profile["name"],
        "email": profile.get("email") or "",
        "phone": profile.get("phone") or "",
        "photo_url": _photo_url(profile),
        "username": profile["username"],
    }
    if profile["role"] == "student":
        row = db.query_one(
            """SELECT s.*, b.name AS batch_name, b.code AS batch_code,
                      b.branch AS batch_branch, b.semester AS batch_semester,
                      b.year AS batch_year
               FROM students s JOIN batches b ON b.id = s.batch_id
               WHERE s.id = ?""",
            (profile["student_id"],),
        )
        base.update({
            "roll_no": row["roll_no"], "full_name": row["full_name"],
            "branch": row["branch"] or row["batch_branch"],
            "semester": row["batch_semester"],
            "batch": row["batch_name"], "batch_code": row["batch_code"],
            "batch_year": row["batch_year"],
            "address": row["address"] or "",
            "guardian_name": row["guardian_name"] or "",
            "guardian_phone": row["guardian_phone"] or "",
            "official": {
                "Name": row["full_name"],
                "Roll No.": row["roll_no"],
                "Branch": row["branch"] or row["batch_branch"],
                "Semester": f"Semester {row['batch_semester']}",
                "Batch": row["batch_name"],
                "Batch code": row["batch_code"],
                "Guardian": row["guardian_name"] or "—",
                "Guardian phone": row["guardian_phone"] or "—",
            },
        })
    else:
        row = db.query_one("SELECT * FROM professors WHERE id = ?",
                           (profile["professor_id"],))
        teachings = db.query(
            """SELECT s.name AS subject_name, s.code AS subject_code, b.name AS batch_name
               FROM professor_batch_subject pbs
               JOIN subjects s ON s.id = pbs.subject_id
               JOIN batches b ON b.id = pbs.batch_id
               WHERE pbs.professor_id = ?
               ORDER BY s.code, b.name""",
            (profile["professor_id"],),
        )
        base.update({
            "employee_id": row["employee_id"], "full_name": row["full_name"],
            "department": row["department"], "designation": row["designation"],
            "qualifications": row["qualifications"] or "",
            "address": row["address"] or "",
            "subjects": teachings,
            "official": {
                "Name": row["full_name"],
                "Employee ID": row["employee_id"],
                "Department": row["department"],
                "Designation": row["designation"],
                "Qualifications": row["qualifications"] or "—",
                "Subjects": ", ".join(sorted({t["subject_code"] for t in teachings})),
            },
        })
    return base


@bp.get("/me")
@api_login_required
def me():
    return json_ok({"profile": detailed_profile(g.user)})


@bp.patch("/me/contact")
@api_login_required
def update_contact():
    data = body()
    fields = {}
    email = str(data.get("email", "")).strip()
    phone = str(data.get("phone", "")).strip()
    address = str(data.get("address", "")).strip()

    if email and not valid_email(email):
        fields["email"] = "Enter a valid email address."
    if phone and not valid_phone(phone):
        fields["phone"] = "Enter a valid phone number (7–18 digits)."
    if len(address) > 255:
        fields["address"] = "Address must be 255 characters or fewer."
    if fields:
        return json_err("Please fix the highlighted fields.", 422, "validation",
                        fields=fields)

    db = get_db()
    if g.user["role"] == "student":
        db.update("students", {"email": email or None, "phone": phone or None,
                               "address": address or None},
                  "id = ?", (g.user["student_id"],))
    else:
        db.update("professors", {"email": email or None, "phone": phone or None,
                                 "address": address or None},
                  "id = ?", (g.user["professor_id"],))
    audit("profile_contact_updated", "user", g.user["user_id"])
    profile = detailed_profile(g.user)
    return json_ok({"profile": profile, "message": "Contact details updated."})


@bp.post("/me/photo")
@api_login_required
def update_photo():
    file = request.files.get("photo")
    if not file:
        return json_err("Choose an image to upload.", 422, "validation",
                        fields={"photo": "Choose an image."})
    try:
        stored = save_upload(file, current_app.config["ALLOWED_PHOTO_EXTENSIONS"])
    except ValueError as exc:
        return json_err(str(exc), 422, "invalid_file", fields={"photo": str(exc)})

    db = get_db()
    table = "students" if g.user["role"] == "student" else "professors"
    entity = g.user.get("student_id") or g.user.get("professor_id")
    previous = db.query_one(f"SELECT photo FROM {table} WHERE id = ?", (entity,))
    db.update(table, {"photo": stored["stored"]}, "id = ?", (entity,))
    if previous and previous.get("photo"):
        delete_upload(previous["photo"])
    audit("profile_photo_updated", "user", g.user["user_id"])

    # refresh cached profile photo
    g.user["photo"] = stored["stored"]
    profile = detailed_profile(g.user)
    return json_ok({"profile": profile, "message": "Profile photo updated."})


@bp.post("/me/password")
@api_login_required
def change_password():
    data = body()
    current = str(data.get("current_password", ""))
    new = str(data.get("new_password", ""))
    confirm = str(data.get("confirm_password", ""))

    fields = {}
    if not current:
        fields["current_password"] = "Enter your current password."
    if len(new) < 8:
        fields["new_password"] = "Use at least 8 characters."
    elif not any(c.isalpha() for c in new) or not any(c.isdigit() for c in new):
        fields["new_password"] = "Include at least one letter and one number."
    if new and confirm and new != confirm:
        fields["confirm_password"] = "Passwords do not match."
    if fields:
        return json_err("Please fix the highlighted fields.", 422, "validation",
                        fields=fields)

    db = get_db()
    user = db.query_one("SELECT password_hash FROM users WHERE id = ?",
                        (g.user["user_id"],))
    if not verify_password(user["password_hash"], current):
        return json_err("Your current password is not correct.", 400,
                        "invalid_current_password",
                        fields={"current_password": "That password is incorrect."})
    if verify_password(user["password_hash"], new):
        return json_err("Choose a password you haven't used before.", 422,
                        "validation",
                        fields={"new_password": "Pick a different password."})

    db.update("users", {"password_hash": hash_password(new), "updated_at": now()},
              "id = ?", (g.user["user_id"],))
    db.execute("DELETE FROM sessions WHERE user_id = ? AND token <> ?",
               (g.user["user_id"], g.session_row["token"]))
    audit("password_changed", "user", g.user["user_id"])
    return json_ok({"message": "Password changed. Other sessions were signed out."})


# --------------------------------------------------------------------------
# Notifications
# --------------------------------------------------------------------------
@bp.get("/notifications")
@api_login_required
def notifications():
    db = get_db()
    page, per, offset = paginate(default_per=15)
    total = db.scalar("SELECT COUNT(*) AS c FROM notifications WHERE user_id = ?",
                      (g.user["user_id"],), default=0)
    unread = db.scalar(
        "SELECT COUNT(*) AS c FROM notifications WHERE user_id = ? AND is_read = 0",
        (g.user["user_id"],), default=0)
    rows = db.query(
        """SELECT id, title, body, link, kind, is_read, created_at
           FROM notifications WHERE user_id = ?
           ORDER BY created_at DESC, id DESC LIMIT ? OFFSET ?""",
        (g.user["user_id"], per, offset),
    )
    return json_ok({
        "items": [{
            "id": r["id"], "title": r["title"], "body": r["body"],
            "link": r["link"], "kind": r["kind"],
            "is_read": bool(r["is_read"]), "created_at": iso(r["created_at"]),
        } for r in rows],
        "unread": unread,
    }, meta=page_meta(page, per, total))


@bp.post("/notifications/read-all")
@api_login_required
def read_all_notifications():
    db = get_db()
    db.execute("UPDATE notifications SET is_read = 1 WHERE user_id = ?",
               (g.user["user_id"],))
    return json_ok({"message": "All notifications marked as read.", "unread": 0})


@bp.post("/notifications/<int:notification_id>/read")
@api_login_required
def read_notification(notification_id: int):
    db = get_db()
    row = db.query_one("SELECT id FROM notifications WHERE id = ? AND user_id = ?",
                       (notification_id, g.user["user_id"]))
    if not row:
        return json_err("Notification not found.", 404, "not_found")
    db.execute("UPDATE notifications SET is_read = 1 WHERE id = ?", (notification_id,))
    unread = db.scalar(
        "SELECT COUNT(*) AS c FROM notifications WHERE user_id = ? AND is_read = 0",
        (g.user["user_id"],), default=0)
    return json_ok({"message": "Marked as read.", "unread": unread})


# --------------------------------------------------------------------------
# Command palette search
# --------------------------------------------------------------------------
@bp.get("/search")
@api_login_required
def search():
    query = (request.args.get("q") or "").strip()
    if len(query) < 2:
        return json_ok({"results": []})
    like = f"%{query}%"
    db = get_db()
    role = g.user["role"]
    results = []

    for label, sub, link in PAGES[role]:
        if query.lower() in label.lower() or query.lower() in sub.lower():
            results.append({"type": "Page", "label": label, "sub": sub, "link": link})

    if role == "student":
        subjects = db.query(
            """SELECT s.code, s.name FROM subjects s
               JOIN batch_subjects bs ON bs.subject_id = s.id
               WHERE bs.batch_id = ? AND (s.name LIKE ? OR s.code LIKE ?)""",
            (g.user["batch_id"], like, like))
        assignments = db.query(
            """SELECT a.id, a.title, s.code FROM assignments a
               JOIN subjects s ON s.id = a.subject_id
               WHERE a.batch_id = ? AND a.deleted_at IS NULL
                 AND a.title LIKE ? LIMIT 5""",
            (g.user["batch_id"], like))
        announcements = db.query(
            """SELECT DISTINCT a.id, a.title FROM announcements a
               LEFT JOIN announcement_targets t ON t.announcement_id = a.id
               WHERE a.deleted_at IS NULL AND a.publish_at <= ?
                 AND (a.audience = 'all' OR t.batch_id = ?)
                 AND a.title LIKE ? LIMIT 5""",
            (now(), g.user["batch_id"], like))
    else:
        subjects = db.query(
            """SELECT DISTINCT s.code, s.name FROM subjects s
               JOIN professor_batch_subject pbs ON pbs.subject_id = s.id
               WHERE pbs.professor_id = ? AND (s.name LIKE ? OR s.code LIKE ?)""",
            (g.user["professor_id"], like, like))
        assignments = db.query(
            """SELECT a.id, a.title, s.code FROM assignments a
               JOIN subjects s ON s.id = a.subject_id
               WHERE a.professor_id = ? AND a.deleted_at IS NULL
                 AND a.title LIKE ? LIMIT 5""",
            (g.user["professor_id"], like))
        announcements = db.query(
            """SELECT id, title FROM announcements
               WHERE professor_id = ? AND deleted_at IS NULL AND title LIKE ?
               LIMIT 5""",
            (g.user["professor_id"], like))

    for subject in subjects:
        results.append({"type": "Subject", "label": subject["name"],
                        "sub": subject["code"], "link": "/#/attendance"})
    for assignment in assignments:
        results.append({"type": "Assignment", "label": assignment["title"],
                        "sub": assignment["code"], "link": "/#/assignments"})
    for announcement in announcements:
        results.append({"type": "Announcement", "label": announcement["title"],
                        "sub": "Notice", "link": "/#/announcements"})

    return json_ok({"results": results[:20], "query": query})


# --------------------------------------------------------------------------
# Campus slideshow images
# --------------------------------------------------------------------------
@bp.get("/campus-images")
def campus_images():
    folder = Path(current_app.static_folder) / "img" / "campus"
    try:
        mtime = folder.stat().st_mtime
    except OSError:
        mtime = 0
    if CAMPUS_CACHE["mtime"] != mtime or not CAMPUS_CACHE["items"]:
        items = []
        if folder.exists():
            for path in sorted(folder.iterdir(), key=lambda p: p.name.lower()):
                if path.suffix.lower() in CAMPUS_EXTENSIONS and path.is_file():
                    items.append({
                        "url": f"/static/img/campus/{path.name}",
                        "name": path.stem.replace("-", " ").replace("_", " ").title(),
                    })
        CAMPUS_CACHE["mtime"] = mtime
        CAMPUS_CACHE["items"] = items
    response = json_ok({"images": CAMPUS_CACHE["items"]})
    response.headers["Cache-Control"] = "public, max-age=300"
    return response


# --------------------------------------------------------------------------
# Authorized file downloads
# --------------------------------------------------------------------------
def _send(stored: str, download_name: str):
    if not stored:
        return json_err("This file is no longer available.", 404, "file_missing")
    path = Path(current_app.config["UPLOAD_DIR"]) / Path(stored).name
    if not path.exists():
        return json_err("This file is no longer available.", 404, "file_missing")
    return send_file(path, as_attachment=True, download_name=download_name,
                     max_age=0)


@bp.get("/files/assignment/<int:assignment_id>")
@api_login_required
def assignment_file(assignment_id: int):
    db = get_db()
    row = db.query_one(
        """SELECT a.*, b.name AS batch_name FROM assignments a
           JOIN batches b ON b.id = a.batch_id WHERE a.id = ?""",
        (assignment_id,),
    )
    if not row:
        return json_err("Assignment not found.", 404, "not_found")
    allowed = False
    if g.user["role"] == "student":
        allowed = row["batch_id"] == g.user["batch_id"] and row["deleted_at"] is None
    else:
        allowed = row["professor_id"] == g.user["professor_id"]
    if not allowed:
        return json_err("You do not have access to this file.", 403, "forbidden")
    if not row.get("attachment_path"):
        return json_err("This assignment has no attachment.", 404, "file_missing")
    return _send(row["attachment_path"], row.get("attachment_name") or "assignment.pdf")


@bp.get("/files/submission/<int:submission_id>")
@api_login_required
def submission_file(submission_id: int):
    db = get_db()
    row = db.query_one(
        """SELECT sub.*, a.professor_id, a.batch_id FROM submissions sub
           JOIN assignments a ON a.id = sub.assignment_id WHERE sub.id = ?""",
        (submission_id,),
    )
    if not row:
        return json_err("Submission not found.", 404, "not_found")
    allowed = (
        (g.user["role"] == "student" and row["student_id"] == g.user["student_id"])
        or (g.user["role"] == "professor"
            and row["professor_id"] == g.user["professor_id"])
    )
    if not allowed:
        return json_err("You do not have access to this file.", 403, "forbidden")
    return _send(row["file_path"], row.get("file_name") or "submission.pdf")


@bp.get("/avatar/<kind>/<int:entity_id>")
@api_login_required
def avatar(kind: str, entity_id: int):
    if kind not in ("student", "professor"):
        return json_err("Not found.", 404, "not_found")
    table = "students" if kind == "student" else "professors"
    db = get_db()
    row = db.query_one(f"SELECT photo FROM {table} WHERE id = ?", (entity_id,))
    if not row or not row.get("photo"):
        return json_err("No photo.", 404, "not_found")
    path = Path(current_app.config["UPLOAD_DIR"]) / Path(row["photo"]).name
    if not path.exists():
        return json_err("No photo.", 404, "not_found")
    response = send_file(path, max_age=300, conditional=True)
    response.headers["Cache-Control"] = "private, max-age=300"
    return response

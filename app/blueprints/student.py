"""Student endpoints: overview, attendance, timetable, assignments, notices."""
from __future__ import annotations

from datetime import date, datetime, timedelta

from flask import Blueprint, current_app, g, request

from ..db import get_db
from ..security import student_required
from ..utils import (
    attendance_stats,
    audit,
    body,
    hhmm,
    iso,
    json_err,
    json_ok,
    notify,
    now,
    page_meta,
    paginate,
    parse_date,
    parse_datetime,
    save_upload,
    delete_upload,
    valid_email,
    valid_phone,
)
from .common import detailed_profile

bp = Blueprint("student", __name__, url_prefix="/api/student")

DAY_NAMES = ["", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday",
             "Saturday", "Sunday"]


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------
def _schedule_for_day(student: dict, day: date) -> list[dict]:
    db = get_db()
    rows = db.query(
        """SELECT t.start_time, t.end_time, t.room, s.code AS subject_code,
                  s.name AS subject_name, p.full_name AS professor_name,
                  p.designation AS professor_designation
           FROM timetable t
           JOIN subjects s ON s.id = t.subject_id
           JOIN professors p ON p.id = t.professor_id
           WHERE t.batch_id = ? AND t.day_of_week = ?
           ORDER BY t.start_time""",
        (student["batch_id"], day.isoweekday()),
    )
    current = now()
    result = []
    for row in rows:
        start = _time_on(day, row["start_time"])
        end = _time_on(day, row["end_time"])
        if current >= end:
            status = "completed"
        elif start <= current < end:
            status = "ongoing"
        else:
            status = "upcoming"
        result.append({
            "start": hhmm(row["start_time"]), "end": hhmm(row["end_time"]),
            "room": row["room"], "subject_code": row["subject_code"],
            "subject_name": row["subject_name"],
            "professor": row["professor_name"],
            "designation": row["professor_designation"],
            "status": status,
        })
    return result


def _time_on(day: date, value) -> datetime:
    text = hhmm(value)
    try:
        hour, minute = int(text[:2]), int(text[3:5])
    except (ValueError, IndexError):
        hour, minute = 0, 0
    return datetime.combine(day, datetime.min.time()).replace(hour=hour, minute=minute)


def _attendance_rows(student: dict, date_from=None, date_to=None):
    sql = """SELECT a.date, a.status, s.code AS subject_code, s.name AS subject_name,
                    s.id AS subject_id, p.full_name AS professor_name
             FROM attendance a
             JOIN subjects s ON s.id = a.subject_id
             LEFT JOIN professors p ON p.id = a.marked_by
             WHERE a.student_id = ?"""
    params = [student["student_id"]]
    if date_from:
        sql += " AND a.date >= ?"
        params.append(date_from)
    if date_to:
        sql += " AND a.date <= ?"
        params.append(date_to)
    sql += " ORDER BY a.date DESC, s.code"
    return get_db().query(sql, tuple(params))


def _subject_summary(student: dict, date_from=None, date_to=None):
    sql = """SELECT s.id AS subject_id, s.code, s.name, s.credits,
                    COUNT(*) AS held,
                    SUM(CASE WHEN a.status IN ('present','late') THEN 1 ELSE 0 END) AS attended,
                    SUM(CASE WHEN a.status = 'absent' THEN 1 ELSE 0 END) AS absent,
                    SUM(CASE WHEN a.status = 'late' THEN 1 ELSE 0 END) AS late,
                    MAX((SELECT p.full_name FROM professor_batch_subject pbs
                         JOIN professors p ON p.id = pbs.professor_id
                         WHERE pbs.subject_id = s.id AND pbs.batch_id = a.batch_id
                         LIMIT 1)) AS professor_name
             FROM attendance a
             JOIN subjects s ON s.id = a.subject_id
             WHERE a.student_id = ?"""
    params = [student["student_id"]]
    if date_from:
        sql += " AND a.date >= ?"
        params.append(date_from)
    if date_to:
        sql += " AND a.date <= ?"
        params.append(date_to)
    sql += " GROUP BY s.id, s.code, s.name, s.credits ORDER BY s.name"
    threshold = current_app.config["ATTENDANCE_THRESHOLD"]
    rows = get_db().query(sql, tuple(params))
    result = []
    for row in rows:
        stats = attendance_stats(row["attended"] or 0, row["held"] or 0, threshold)
        result.append({
            "subject_id": row["subject_id"], "code": row["code"],
            "name": row["name"], "credits": row["credits"],
            "professor": row["professor_name"],
            "late": int(row["late"] or 0),
            "absent": int(row["absent"] or 0),
            **stats,
        })
    return result


def _overall(student: dict, date_from=None, date_to=None):
    sql = """SELECT COUNT(*) AS held,
                    SUM(CASE WHEN status IN ('present','late') THEN 1 ELSE 0 END) AS attended,
                    SUM(CASE WHEN status = 'absent' THEN 1 ELSE 0 END) AS absent
             FROM attendance WHERE student_id = ?"""
    params = [student["student_id"]]
    if date_from:
        sql += " AND date >= ?"
        params.append(date_from)
    if date_to:
        sql += " AND date <= ?"
        params.append(date_to)
    row = get_db().query_one(sql, tuple(params)) or {}
    stats = attendance_stats(row.get("attended") or 0, row.get("held") or 0,
                             current_app.config["ATTENDANCE_THRESHOLD"])
    stats["absent"] = int(row.get("absent") or 0)
    return stats


def _trend(rows: list[dict], weeks: int = 6):
    """Weekly attendance percentages for the mini trend chart."""
    today = date.today()
    start = today - timedelta(days=today.weekday() + 7 * (weeks - 1))
    buckets = []
    for index in range(weeks):
        week_start = start + timedelta(days=7 * index)
        week_end = week_start + timedelta(days=6)
        buckets.append({
            "label": week_start.strftime("%d %b"),
            "start": week_start.isoformat(),
            "end": week_end.isoformat(),
            "attended": 0, "held": 0,
        })
    for row in rows:
        day = parse_date(str(row["date"])[:10])
        if not day:
            continue
        for bucket in buckets:
            if bucket["start"] <= day.isoformat() <= bucket["end"]:
                bucket["held"] += 1
                if row["status"] in ("present", "late"):
                    bucket["attended"] += 1
                break
    return [{
        "label": b["label"],
        "percentage": round(b["attended"] * 100 / b["held"], 1) if b["held"] else None,
        "held": b["held"],
    } for b in buckets]


def _monthly_trend(rows: list[dict], months: int = 6):
    today = date.today()
    buckets = []
    cursor = date(today.year, today.month, 1)
    for _ in range(months):
        buckets.insert(0, {
            "key": cursor.strftime("%Y-%m"),
            "label": cursor.strftime("%b %Y"),
            "attended": 0, "held": 0,
        })
        cursor = (cursor - timedelta(days=1)).replace(day=1)
    for row in rows:
        key = str(row["date"])[:7]
        for bucket in buckets:
            if bucket["key"] == key:
                bucket["held"] += 1
                if row["status"] in ("present", "late"):
                    bucket["attended"] += 1
                break
    return [{
        "label": b["label"],
        "percentage": round(b["attended"] * 100 / b["held"], 1) if b["held"] else None,
        "held": b["held"],
    } for b in buckets]


def _announcement_scope(student: dict):
    return """a.deleted_at IS NULL AND a.publish_at <= ?
              AND (a.audience = 'all' OR EXISTS (
                  SELECT 1 FROM announcement_targets t
                  WHERE t.announcement_id = a.id AND t.batch_id = ?))"""


def _announcement_payload(rows, user_id):
    if not rows:
        return []
    db = get_db()
    ids = [r["id"] for r in rows]
    marks = ", ".join("?" for _ in ids)
    targets = db.query(
        f"""SELECT t.announcement_id, b.name FROM announcement_targets t
            JOIN batches b ON b.id = t.batch_id
            WHERE t.announcement_id IN ({marks})""",
        tuple(ids),
    )
    tag_map: dict[int, list[str]] = {}
    for target in targets:
        tag_map.setdefault(target["announcement_id"], []).append(target["name"])
    payload = []
    for row in rows:
        read = (row.get("read_count") or 0) > 0
        payload.append({
            "id": row["id"], "title": row["title"], "body": row["body"],
            "priority": row["priority"], "pinned": bool(row["pinned"]),
            "audience": row["audience"],
            "professor": row["professor_name"],
            "publish_at": iso(row["publish_at"]),
            "is_read": read,
            "batches": tag_map.get(row["id"], []),
        })
    return payload


def _visible_announcements(student, limit=None, unread_only=False, priority=None,
                           query=None, page=1, per_page=None, date_from=None,
                           date_to=None):
    db = get_db()
    scope = _announcement_scope(student)
    sql = f"""SELECT a.*, p.full_name AS professor_name,
                     (SELECT COUNT(*) FROM announcement_reads ar
                      WHERE ar.announcement_id = a.id AND ar.user_id = ?) AS read_count
              FROM announcements a
              JOIN professors p ON p.id = a.professor_id
              WHERE {scope}"""
    params = [student["user_id"], now(), student["batch_id"]]
    if unread_only:
        sql += """ AND NOT EXISTS (SELECT 1 FROM announcement_reads ar2
                   WHERE ar2.announcement_id = a.id AND ar2.user_id = ?)"""
        params.append(student["user_id"])
    if priority in ("normal", "important", "urgent"):
        sql += " AND a.priority = ?"
        params.append(priority)
    if query:
        sql += " AND (a.title LIKE ? OR a.body LIKE ?)"
        params.extend([f"%{query}%", f"%{query}%"])
    if date_from:
        sql += " AND a.publish_at >= ?"
        params.append(datetime.combine(date_from, datetime.min.time()))
    if date_to:
        sql += " AND a.publish_at <= ?"
        params.append(datetime.combine(date_to, datetime.max.time()))
    sql += " ORDER BY a.pinned DESC, a.publish_at DESC, a.id DESC"
    count_sql = f"SELECT COUNT(*) AS c FROM announcements a WHERE {scope}"
    count_params = [now(), student["batch_id"]]
    if unread_only:
        count_sql += """ AND NOT EXISTS (SELECT 1 FROM announcement_reads ar2
                         WHERE ar2.announcement_id = a.id AND ar2.user_id = ?)"""
        count_params.append(student["user_id"])
    if priority in ("normal", "important", "urgent"):
        count_sql += " AND a.priority = ?"
        count_params.append(priority)
    if query:
        count_sql += " AND (a.title LIKE ? OR a.body LIKE ?)"
        count_params.extend([f"%{query}%", f"%{query}%"])
    if date_from:
        count_sql += " AND a.publish_at >= ?"
        count_params.append(datetime.combine(date_from, datetime.min.time()))
    if date_to:
        count_sql += " AND a.publish_at <= ?"
        count_params.append(datetime.combine(date_to, datetime.max.time()))

    total = db.scalar(count_sql, tuple(count_params), default=0)
    if per_page:
        sql += " LIMIT ? OFFSET ?"
        params.extend([per_page, max(0, (page - 1) * per_page)])
    elif limit:
        sql += " LIMIT ?"
        params.append(limit)
    rows = db.query(sql, tuple(params))
    items = _announcement_payload(rows, student["user_id"])
    return items, total


def _assignment_rows(student: dict):
    return get_db().query(
        """SELECT a.id, a.title, a.description, a.due_date, a.max_marks,
                  a.attachment_name, a.attachment_path, a.created_at,
                  s.code AS subject_code, s.name AS subject_name,
                  p.full_name AS professor_name,
                  sub.id AS submission_id, sub.status AS submission_status,
                  sub.marks, sub.remarks, sub.submitted_at, sub.file_name,
                  sub.file_path
           FROM assignments a
           JOIN subjects s ON s.id = a.subject_id
           JOIN professors p ON p.id = a.professor_id
           LEFT JOIN submissions sub
                  ON sub.assignment_id = a.id AND sub.student_id = ?
           WHERE a.batch_id = ? AND a.deleted_at IS NULL
           ORDER BY s.name, a.due_date""",
        (student["student_id"], student["batch_id"]),
    )


def _assignment_status(row) -> str:
    if row["submission_status"] == "graded":
        return "graded"
    if row["submission_id"]:
        return "submitted"
    due = parse_datetime(row["due_date"])
    if due and due < now():
        return "overdue"
    return "pending"


# --------------------------------------------------------------------------
# Overview
# --------------------------------------------------------------------------
@bp.get("/overview")
@student_required
def overview():
    student = g.user
    db = get_db()
    today = date.today()
    overall = _overall(student)
    subjects = _subject_summary(student)
    history = _attendance_rows(student, today - timedelta(days=42), today)
    schedule = _schedule_for_day(student, today)

    notices, _ = _visible_announcements(student, limit=5)
    unread_notices = db.scalar(
        f"""SELECT COUNT(*) AS c FROM announcements a
            WHERE {_announcement_scope(student)}
              AND NOT EXISTS (SELECT 1 FROM announcement_reads ar
                              WHERE ar.announcement_id = a.id AND ar.user_id = ?)""",
        (now(), student["batch_id"], student["user_id"]), default=0)

    assignments = _assignment_rows(student)
    assignment_cards = []
    for row in assignments:
        status = _assignment_status(row)
        assignment_cards.append({
            "id": row["id"], "title": row["title"], "subject": row["subject_name"],
            "subject_code": row["subject_code"], "due_date": iso(row["due_date"]),
            "status": status, "max_marks": row["max_marks"],
        })
    pending = [a for a in assignment_cards if a["status"] in ("pending", "overdue")]
    pending.sort(key=lambda a: a["due_date"] or "")

    next_class = next((c for c in schedule if c["status"] != "completed"), None)
    stats = db.query_one(
        """SELECT (SELECT COUNT(*) FROM batch_subjects WHERE batch_id = ?) AS subjects,
                  (SELECT COUNT(*) FROM notifications
                   WHERE user_id = ? AND is_read = 0) AS unread"""
        , (student["batch_id"], student["user_id"])) or {}

    return json_ok({
        "student": {
            "name": student["name"], "roll_no": student["roll_no"],
            "batch": student["batch"], "batch_code": student["batch_code"],
            "branch": student["branch"], "semester": student["semester"],
            "photo_url": f"/api/common/avatar/student/{student['student_id']}"
                         if student.get("photo") else "",
        },
        "attendance": overall,
        "subjects": subjects,
        "trend": _trend(history, weeks=6),
        "schedule": schedule,
        "next_class": next_class,
        "announcements": notices,
        "unread_announcements": unread_notices,
        "assignments": assignment_cards[:6],
        "pending_assignments": len(pending),
        "quick_stats": {
            "subjects": int(stats.get("subjects") or 0),
            "unread_notifications": int(stats.get("unread") or 0),
            "classes_today": len(schedule),
            "pending_assignments": len(pending),
        },
        "today": today.isoformat(),
        "day_name": DAY_NAMES[today.isoweekday()],
    })


# --------------------------------------------------------------------------
# Attendance
# --------------------------------------------------------------------------
@bp.get("/attendance")
@student_required
def attendance():
    student = g.user
    today = date.today()
    date_from = parse_date(request.args.get("from"), today - timedelta(days=90))
    date_to = parse_date(request.args.get("to"), today)
    if not date_from or not date_to:
        return json_err("Use dates in YYYY-MM-DD format.", 422, "validation")
    if date_from > date_to:
        return json_err("The start date must be before the end date.", 422,
                        "validation")
    if (date_to - date_from).days > 366:
        return json_err("Choose a range of one year or less.", 422, "validation")

    rows = _attendance_rows(student, date_from, date_to)
    page, per, offset = paginate(default_per=15, max_per=100)
    total = len(rows)
    sliced = rows[offset:offset + per]
    records = [{
        "date": iso(row["date"]), "status": row["status"],
        "subject_code": row["subject_code"], "subject_name": row["subject_name"],
        "professor": row["professor_name"],
    } for row in sliced]

    return json_ok({
        "overall": _overall(student, date_from, date_to),
        "subjects": _subject_summary(student, date_from, date_to),
        "monthly_trend": _monthly_trend(rows),
        "records": records,
        "range": {"from": date_from.isoformat(), "to": date_to.isoformat()},
    }, meta=page_meta(page, per, total))


# --------------------------------------------------------------------------
# Timetable
# --------------------------------------------------------------------------
@bp.get("/timetable")
@student_required
def timetable():
    student = g.user
    rows = get_db().query(
        """SELECT t.day_of_week, t.start_time, t.end_time, t.room,
                  s.code AS subject_code, s.name AS subject_name,
                  p.full_name AS professor_name
           FROM timetable t
           JOIN subjects s ON s.id = t.subject_id
           JOIN professors p ON p.id = t.professor_id
           WHERE t.batch_id = ?
           ORDER BY t.day_of_week, t.start_time""",
        (student["batch_id"],),
    )
    days = []
    for number in range(1, 7):
        classes = [{
            "start": hhmm(r["start_time"]), "end": hhmm(r["end_time"]),
            "room": r["room"], "subject_code": r["subject_code"],
            "subject_name": r["subject_name"], "professor": r["professor_name"],
        } for r in rows if r["day_of_week"] == number]
        days.append({"day": DAY_NAMES[number], "day_number": number,
                     "classes": classes})
    return json_ok({"days": days, "today": date.today().isoweekday(),
                    "batch": student["batch"]})


# --------------------------------------------------------------------------
# Assignments
# --------------------------------------------------------------------------
@bp.get("/assignments")
@student_required
def assignments():
    rows = _assignment_rows(g.user)
    items = []
    for row in rows:
        items.append({
            "id": row["id"], "title": row["title"], "description": row["description"],
            "due_date": iso(row["due_date"]), "max_marks": row["max_marks"],
            "subject_code": row["subject_code"], "subject_name": row["subject_name"],
            "professor": row["professor_name"],
            "attachment": {
                "name": row["attachment_name"],
                "url": f"/api/common/files/assignment/{row['id']}"
            } if row["attachment_path"] else None,
            "status": _assignment_status(row),
            "submission": {
                "id": row["submission_id"],
                "status": row["submission_status"],
                "marks": float(row["marks"]) if row["marks"] is not None else None,
                "remarks": row["remarks"],
                "submitted_at": iso(row["submitted_at"]),
                "file_name": row["file_name"],
                "download_url": f"/api/common/files/submission/{row['submission_id']}"
                if row["file_path"] else None,
            } if row["submission_id"] else None,
        })
    return json_ok({"items": items, "today": now().isoformat()})


@bp.post("/assignments/<int:assignment_id>/submit")
@student_required
def submit_assignment(assignment_id: int):
    db = get_db()
    student = g.user
    assignment = db.query_one(
        """SELECT * FROM assignments
           WHERE id = ? AND batch_id = ? AND deleted_at IS NULL""",
        (assignment_id, student["batch_id"]),
    )
    if not assignment:
        return json_err("Assignment not found for your batch.", 404, "not_found")

    existing = db.query_one(
        "SELECT * FROM submissions WHERE assignment_id = ? AND student_id = ?",
        (assignment_id, student["student_id"]),
    )
    if existing and existing["status"] == "graded":
        return json_err("This submission has already been graded and can't be replaced.",
                        409, "already_graded")

    upload = request.files.get("file")
    if not upload:
        return json_err("Attach your submission file.", 422, "validation",
                        fields={"file": "Choose a file to upload."})
    try:
        stored = save_upload(upload)
    except ValueError as exc:
        return json_err(str(exc), 422, "invalid_file", fields={"file": str(exc)})

    submitted_at = now()
    if existing:
        old_file = existing.get("file_path")
        db.update("submissions", {
            "file_path": stored["stored"], "file_name": stored["name"],
            "file_size": stored["size"], "submitted_at": submitted_at,
            "status": "submitted",
        }, "id = ?", (existing["id"],))
        if old_file:
            delete_upload(old_file)
        submission_id = existing["id"]
    else:
        submission_id = db.insert("submissions", {
            "assignment_id": assignment_id, "student_id": student["student_id"],
            "file_path": stored["stored"], "file_name": stored["name"],
            "file_size": stored["size"], "submitted_at": submitted_at,
            "status": "submitted",
        })

    professor = db.query_one("SELECT user_id FROM professors WHERE id = ?",
                             (assignment["professor_id"],))
    if professor:
        notify(professor["user_id"], "New submission received",
               f"{student['name']} ({student['roll_no']}) submitted "
               f"“{assignment['title']}”.",
               "/#/assignments", "assignment")
    audit("assignment_submitted", "assignment", assignment_id,
          f"submission={submission_id}")

    return json_ok({
        "message": "Submission uploaded successfully.",
        "submission": {
            "id": submission_id, "file_name": stored["name"],
            "submitted_at": iso(submitted_at),
            "download_url": f"/api/common/files/submission/{submission_id}",
        },
    }, status=201)


# --------------------------------------------------------------------------
# Announcements
# --------------------------------------------------------------------------
@bp.get("/announcements")
@student_required
def announcements():
    student = g.user
    page, per, _offset = paginate(default_per=10)
    unread_only = request.args.get("unread") == "1"
    priority = request.args.get("priority")
    query = (request.args.get("q") or "").strip() or None
    date_from = parse_date(request.args.get("from"))
    date_to = parse_date(request.args.get("to"))
    if request.args.get("from") and not date_from:
        return json_err("Use dates in YYYY-MM-DD format.", 422, "validation")
    if request.args.get("to") and not date_to:
        return json_err("Use dates in YYYY-MM-DD format.", 422, "validation")
    items, total = _visible_announcements(
        student, unread_only=unread_only, priority=priority,
        query=query, page=page, per_page=per,
        date_from=date_from, date_to=date_to,
    )
    return json_ok({"items": items, "unread_only": unread_only},
                   meta=page_meta(page, per, total))


@bp.post("/announcements/read")
@student_required
def mark_announcements_read():
    data = body()
    db = get_db()
    student = g.user
    if data.get("all"):
        rows = db.query(
            f"""SELECT a.id FROM announcements a
                WHERE {_announcement_scope(student)}
                  AND NOT EXISTS (SELECT 1 FROM announcement_reads ar
                                  WHERE ar.announcement_id = a.id AND ar.user_id = ?)""",
            (now(), student["batch_id"], student["user_id"]),
        )
        for row in rows:
            db.insert("announcement_reads", {
                "announcement_id": row["id"], "user_id": student["user_id"],
                "read_at": now(),
            })
        return json_ok({"message": f"{len(rows)} announcement(s) marked as read.",
                        "marked": len(rows)})

    try:
        announcement_id = int(data.get("id"))
    except (TypeError, ValueError):
        return json_err("Choose an announcement to mark as read.", 422, "validation")

    visible = db.query_one(
        f"SELECT a.id FROM announcements a WHERE a.id = ? AND {_announcement_scope(student)}",
        (announcement_id, now(), student["batch_id"]),
    )
    if not visible:
        return json_err("Announcement not found.", 404, "not_found")
    exists = db.query_one(
        "SELECT id FROM announcement_reads WHERE announcement_id = ? AND user_id = ?",
        (announcement_id, student["user_id"]),
    )
    if not exists:
        db.insert("announcement_reads", {
            "announcement_id": announcement_id, "user_id": student["user_id"],
            "read_at": now(),
        })
    return json_ok({"message": "Marked as read."})


# --------------------------------------------------------------------------
# Today's schedule
# --------------------------------------------------------------------------
@bp.get("/schedule/today")
@student_required
def schedule_today():
    today = date.today()
    schedule = _schedule_for_day(g.user, today)
    return json_ok({
        "date": today.isoformat(),
        "day_name": DAY_NAMES[today.isoweekday()],
        "classes": schedule,
        "now": now().isoformat(),
    })


# --------------------------------------------------------------------------
# Profile
# --------------------------------------------------------------------------
@bp.get("/profile")
@student_required
def profile():
    return json_ok({"profile": detailed_profile(g.user)})


@bp.patch("/profile")
@student_required
def update_profile():
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
    db.update("students", {"email": email or None, "phone": phone or None,
                           "address": address or None},
              "id = ?", (g.user["student_id"],))
    g.user.update({"email": email, "phone": phone})
    audit("student_profile_updated", "student", g.user["student_id"])
    return json_ok({"profile": detailed_profile(g.user),
                    "message": "Profile updated."})

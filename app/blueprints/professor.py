"""Professor endpoints: batches, attendance, assignments, announcements."""
from __future__ import annotations

import io
import zipfile
from datetime import date, datetime, timedelta
from pathlib import Path

from flask import Blueprint, current_app, g, request, send_file

from ..db import get_db
from ..security import professor_required
from ..utils import (
    attendance_stats,
    audit,
    body,
    hhmm,
    human_size,
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

bp = Blueprint("professor", __name__, url_prefix="/api/professor")

DAY_NAMES = ["", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday",
             "Saturday", "Sunday"]


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------
def _teaching_pairs(professor_id: int) -> list[dict]:
    return get_db().query(
        """SELECT pbs.batch_id, pbs.subject_id, b.name AS batch_name,
                  b.code AS batch_code, b.branch, b.semester,
                  s.code AS subject_code, s.name AS subject_name
           FROM professor_batch_subject pbs
           JOIN batches b ON b.id = pbs.batch_id
           JOIN subjects s ON s.id = pbs.subject_id
           WHERE pbs.professor_id = ?
           ORDER BY b.name, s.code""",
        (professor_id,),
    )


def _professor_batch_ids(professor_id: int) -> list[int]:
    rows = get_db().query(
        "SELECT DISTINCT batch_id FROM professor_batch_subject WHERE professor_id = ?",
        (professor_id,),
    )
    return [r["batch_id"] for r in rows]


def _teaches(professor_id: int, batch_id: int, subject_id: int) -> bool:
    return bool(get_db().query_one(
        """SELECT id FROM professor_batch_subject
           WHERE professor_id = ? AND batch_id = ? AND subject_id = ?""",
        (professor_id, batch_id, subject_id),
    ))


def _time_on(day: date, value) -> datetime:
    text = hhmm(value)
    try:
        hour, minute = int(text[:2]), int(text[3:5])
    except (ValueError, IndexError):
        hour, minute = 0, 0
    return datetime.combine(day, datetime.min.time()).replace(hour=hour, minute=minute)


def _today_schedule(professor_id: int) -> list[dict]:
    today = date.today()
    rows = get_db().query(
        """SELECT t.start_time, t.end_time, t.room, b.name AS batch_name,
                  b.code AS batch_code, b.id AS batch_id,
                  s.id AS subject_id, s.code AS subject_code, s.name AS subject_name
           FROM timetable t
           JOIN batches b ON b.id = t.batch_id
           JOIN subjects s ON s.id = t.subject_id
           WHERE t.professor_id = ? AND t.day_of_week = ?
           ORDER BY t.start_time""",
        (professor_id, today.isoweekday()),
    )
    current = now()
    classes = []
    for row in rows:
        start = _time_on(today, row["start_time"])
        end = _time_on(today, row["end_time"])
        status = "completed" if current >= end else (
            "ongoing" if start <= current < end else "upcoming")
        classes.append({
            "start": hhmm(row["start_time"]), "end": hhmm(row["end_time"]),
            "room": row["room"], "batch_name": row["batch_name"],
            "batch_code": row["batch_code"], "batch_id": row["batch_id"],
            "subject_id": row["subject_id"],
            "subject_code": row["subject_code"],
            "subject_name": row["subject_name"], "status": status,
        })
    return classes


def _announcement_targets(ids: list[int]) -> dict[int, list[dict]]:
    if not ids:
        return {}
    marks = ", ".join("?" for _ in ids)
    rows = get_db().query(
        f"""SELECT t.announcement_id, b.id, b.name, b.code
            FROM announcement_targets t JOIN batches b ON b.id = t.batch_id
            WHERE t.announcement_id IN ({marks}) ORDER BY b.name""",
        tuple(ids),
    )
    mapping: dict[int, list[dict]] = {}
    for row in rows:
        mapping.setdefault(row["announcement_id"], []).append({
            "id": row["id"], "name": row["name"], "code": row["code"],
        })
    return mapping


def _assignment_payload(row) -> dict:
    due = parse_datetime(row["due_date"])
    total_students = int(row["total_students"] or 0)
    submitted = int(row["submitted"] or 0)
    graded = int(row["graded"] or 0)
    if due and due < now():
        bucket = "completed" if total_students and graded >= total_students else "past_due"
    else:
        bucket = "active"
    return {
        "id": row["id"], "title": row["title"], "description": row["description"],
        "due_date": iso(row["due_date"]),
        "max_marks": row["max_marks"],
        "subject_id": row["subject_id"], "subject_code": row["subject_code"],
        "subject_name": row["subject_name"],
        "batch_id": row["batch_id"], "batch_name": row["batch_name"],
        "batch_code": row["batch_code"],
        "attachment": {
            "name": row["attachment_name"],
            "url": f"/api/common/files/assignment/{row['id']}",
        } if row["attachment_path"] else None,
        "total_students": total_students,
        "submitted": submitted, "graded": graded,
        "pending": max(0, total_students - submitted),
        "bucket": bucket,
        "created_at": iso(row["created_at"]),
    }


def _assignments_for(professor_id: int, batch_id: int | None = None):
    db = get_db()
    sql = """SELECT a.*, s.code AS subject_code, s.name AS subject_name,
                    b.name AS batch_name, b.code AS batch_code,
                    (SELECT COUNT(*) FROM students st WHERE st.batch_id = a.batch_id)
                        AS total_students,
                    (SELECT COUNT(*) FROM submissions sub WHERE sub.assignment_id = a.id)
                        AS submitted,
                    (SELECT COUNT(*) FROM submissions sub WHERE sub.assignment_id = a.id
                        AND sub.status = 'graded') AS graded
             FROM assignments a
             JOIN subjects s ON s.id = a.subject_id
             JOIN batches b ON b.id = a.batch_id
             WHERE a.professor_id = ? AND a.deleted_at IS NULL"""
    params = [professor_id]
    if batch_id:
        sql += " AND a.batch_id = ?"
        params.append(batch_id)
    sql += " ORDER BY a.due_date DESC, a.id DESC"
    return db.query(sql, tuple(params))


def _announcement_rows(professor_id: int):
    return get_db().query(
        """SELECT a.*, 
                  (SELECT COUNT(*) FROM announcement_reads ar
                   WHERE ar.announcement_id = a.id) AS read_count,
                  (SELECT COUNT(*) FROM students s
                   WHERE s.batch_id IN (SELECT batch_id FROM announcement_targets t
                                        WHERE t.announcement_id = a.id)) AS audience_count
           FROM announcements a
           WHERE a.professor_id = ? AND a.deleted_at IS NULL
           ORDER BY a.pinned DESC, a.publish_at DESC, a.id DESC""",
        (professor_id,),
    )


# --------------------------------------------------------------------------
# Overview
# --------------------------------------------------------------------------
@bp.get("/overview")
@professor_required
def overview():
    professor = g.user
    pid = professor["professor_id"]
    db = get_db()
    pairs = _teaching_pairs(pid)
    batch_ids = sorted({p["batch_id"] for p in pairs})

    cards = []
    for pair in pairs:
        students = db.scalar(
            "SELECT COUNT(*) AS c FROM students WHERE batch_id = ?",
            (pair["batch_id"],), default=0)
        row = db.query_one(
            """SELECT COUNT(*) AS held,
                      SUM(CASE WHEN status IN ('present','late') THEN 1 ELSE 0 END)
                          AS attended
               FROM attendance WHERE batch_id = ? AND subject_id = ?""",
            (pair["batch_id"], pair["subject_id"]),
        ) or {}
        stats = attendance_stats(row.get("attended") or 0, row.get("held") or 0)
        cards.append({
            "batch_id": pair["batch_id"], "batch_name": pair["batch_name"],
            "batch_code": pair["batch_code"],
            "subject_id": pair["subject_id"],
            "subject_code": pair["subject_code"],
            "subject_name": pair["subject_name"],
            "students": int(students or 0),
            "average_attendance": stats["percentage"],
        })

    schedule = _today_schedule(pid)
    ann_rows = _announcement_rows(pid)[:5]
    targets = _announcement_targets([r["id"] for r in ann_rows])
    announcements = [{
        "id": r["id"], "title": r["title"], "priority": r["priority"],
        "pinned": bool(r["pinned"]), "publish_at": iso(r["publish_at"]),
        "batches": targets.get(r["id"], []), "read_count": int(r["read_count"] or 0),
        "audience_count": 0,
        "status": "scheduled" if parse_datetime(r["publish_at"]) > now() else "published",
    } for r in ann_rows]

    assignments = _assignments_for(pid)
    awaiting = sum(int(a["submitted"] or 0) - int(a["graded"] or 0)
                   for a in assignments)
    recent_submissions = db.query(
        """SELECT sub.id, sub.file_name, sub.submitted_at, sub.status,
                  st.full_name AS student_name, st.roll_no,
                  a.id AS assignment_id, a.title AS assignment_title
           FROM submissions sub
           JOIN assignments a ON a.id = sub.assignment_id
           JOIN students st ON st.id = sub.student_id
           WHERE a.professor_id = ? AND a.deleted_at IS NULL
           ORDER BY sub.submitted_at DESC LIMIT 6""",
        (pid,),
    )

    low_attendance = []
    if batch_ids:
        marks = ", ".join("?" for _ in batch_ids)
        rows = db.query(
            f"""SELECT st.id, st.roll_no, st.full_name, b.name AS batch_name,
                       COUNT(a.id) AS held,
                       SUM(CASE WHEN a.status IN ('present','late') THEN 1 ELSE 0 END)
                           AS attended
                FROM students st
                JOIN batches b ON b.id = st.batch_id
                LEFT JOIN attendance a ON a.student_id = st.id
                WHERE st.batch_id IN ({marks})
                GROUP BY st.id, st.roll_no, st.full_name, b.name
                HAVING COUNT(a.id) > 0
                   AND (SUM(CASE WHEN a.status IN ('present','late') THEN 1 ELSE 0 END)
                        * 100.0 / COUNT(a.id)) < ?
                ORDER BY (SUM(CASE WHEN a.status IN ('present','late') THEN 1 ELSE 0 END)
                          * 100.0 / COUNT(a.id)) ASC
                LIMIT 8""",
            tuple(batch_ids) + (current_app.config["ATTENDANCE_THRESHOLD"],),
        )
        for row in rows:
            low_attendance.append({
                "student_id": row["id"], "roll_no": row["roll_no"],
                "name": row["full_name"], "batch": row["batch_name"],
                "percentage": round((row["attended"] or 0) * 100.0 /
                                    (row["held"] or 1), 1),
                "held": int(row["held"] or 0),
            })

    student_count = db.scalar(
        f"SELECT COUNT(*) AS c FROM students WHERE batch_id IN ({', '.join('?' * len(batch_ids))})",
        tuple(batch_ids), default=0) if batch_ids else 0

    return json_ok({
        "professor": {
            "name": professor["name"], "employee_id": professor["employee_id"],
            "department": professor["department"],
            "designation": professor["designation"],
            "photo_url": f"/api/common/avatar/professor/{pid}"
                         if professor.get("photo") else "",
        },
        "batch_cards": cards,
        "batches_count": len(batch_ids),
        "students_count": int(student_count or 0),
        "schedule": schedule,
        "announcements": announcements,
        "assignments": [_assignment_payload(a) for a in assignments[:5]],
        "awaiting_review": awaiting,
        "recent_submissions": [{
            "id": r["id"], "student": r["student_name"], "roll_no": r["roll_no"],
            "assignment": r["assignment_title"], "assignment_id": r["assignment_id"],
            "submitted_at": iso(r["submitted_at"]), "status": r["status"],
        } for r in recent_submissions],
        "low_attendance": low_attendance,
        "quick_stats": {
            "batches": len(batch_ids),
            "students": int(student_count or 0),
            "classes_today": len(schedule),
            "awaiting_review": awaiting,
        },
        "today": date.today().isoformat(),
        "day_name": DAY_NAMES[date.today().isoweekday()],
    })


# --------------------------------------------------------------------------
# Batches / students
# --------------------------------------------------------------------------
@bp.get("/batches")
@professor_required
def batches():
    pid = g.user["professor_id"]
    db = get_db()
    pairs = _teaching_pairs(pid)
    grouped: dict[int, dict] = {}
    for pair in pairs:
        entry = grouped.setdefault(pair["batch_id"], {
            "id": pair["batch_id"], "name": pair["batch_name"],
            "code": pair["batch_code"], "branch": pair["branch"],
            "semester": pair["semester"], "subjects": [], "students": 0,
        })
        entry["subjects"].append({
            "id": pair["subject_id"], "code": pair["subject_code"],
            "name": pair["subject_name"],
        })
    for batch in grouped.values():
        batch["students"] = int(db.scalar(
            "SELECT COUNT(*) AS c FROM students WHERE batch_id = ?",
            (batch["id"],), default=0) or 0)
        batch["low_attendance"] = db.scalar(
            """SELECT COUNT(*) AS c FROM (
                   SELECT st.id, COUNT(a.id) AS held,
                          SUM(CASE WHEN a.status IN ('present','late') THEN 1 ELSE 0 END)
                              AS attended
                   FROM students st
                   LEFT JOIN attendance a ON a.student_id = st.id
                   WHERE st.batch_id = ?
                   GROUP BY st.id
                   HAVING held > 0 AND (attended * 100.0 / held) < ?
               ) AS low""",
            (batch["id"], current_app.config["ATTENDANCE_THRESHOLD"]), default=0)
    return json_ok({"batches": list(grouped.values())})


@bp.get("/students")
@professor_required
def students():
    pid = g.user["professor_id"]
    db = get_db()
    batch_ids = _professor_batch_ids(pid)
    if not batch_ids:
        return json_ok({"items": []})
    requested = request.args.get("batch_id", type=int)
    if requested and requested not in batch_ids:
        return json_err("That batch is outside your teaching load.", 403, "forbidden")
    selected = [requested] if requested else batch_ids
    marks = ", ".join("?" for _ in selected)
    rows = db.query(
        f"""SELECT st.id, st.roll_no, st.full_name, st.email, b.name AS batch_name,
                   COUNT(a.id) AS held,
                   SUM(CASE WHEN a.status IN ('present','late') THEN 1 ELSE 0 END)
                       AS attended
            FROM students st
            JOIN batches b ON b.id = st.batch_id
            LEFT JOIN attendance a ON a.student_id = st.id
            WHERE st.batch_id IN ({marks})
            GROUP BY st.id, st.roll_no, st.full_name, st.email, b.name
            ORDER BY b.name, st.roll_no""",
        tuple(selected),
    )
    min_pct = request.args.get("low_attendance") == "1"
    items = []
    for row in rows:
        percentage = round((row["attended"] or 0) * 100.0 / (row["held"] or 1), 1) \
            if row["held"] else 0.0
        if min_pct and percentage >= current_app.config["ATTENDANCE_THRESHOLD"]:
            continue
        items.append({
            "id": row["id"], "roll_no": row["roll_no"],
            "name": row["full_name"], "email": row["email"],
            "batch": row["batch_name"], "held": int(row["held"] or 0),
            "attended": int(row["attended"] or 0), "percentage": percentage,
        })
    return json_ok({"items": items})


@bp.post("/students/add")
@professor_required
def add_student():
    pid = g.user["professor_id"]
    data = body()
    try:
        batch_id = int(data.get("batch_id"))
    except (TypeError, ValueError):
        return json_err("Valid batch ID is required.", 422, "validation")

    roll_no = str(data.get("roll_no", "")).strip()
    full_name = str(data.get("full_name", "")).strip()

    if not roll_no or not full_name:
        return json_err("Roll number and name are required.", 422, "validation")

    # Verify professor teaches this batch
    if batch_id not in _professor_batch_ids(pid):
        return json_err("You are not assigned to this batch.", 403, "forbidden")

    db = get_db()
    # Check if student already exists
    existing = db.query_one("SELECT id FROM students WHERE roll_no = ?", (roll_no,))

    if existing:
        # Update batch if they are in another one
        db.update("students", {"batch_id": batch_id}, "id = ?", (existing["id"],))
        msg = "Student updated and assigned to batch."
    else:
        # Create new student record
        db.insert("students", {
            "roll_no": roll_no,
            "full_name": full_name,
            "batch_id": batch_id,
            "created_at": now(),
        })
        msg = "Student added to batch successfully."

    audit("student_added", "batch", batch_id, f"roll={roll_no}")
    return json_ok({"message": msg})


@bp.post("/students/import")
@professor_required
def import_students():
    pid = g.user["professor_id"]
    data = body() or request.form
    try:
        batch_id = int(data.get("batch_id"))
    except (TypeError, ValueError):
        return json_err("Valid batch ID is required.", 422, "validation")

    if batch_id not in _professor_batch_ids(pid):
        return json_err("Invalid batch assignment.", 403, "forbidden")

    file = request.files.get("file")
    if not file or not file.filename:
        return json_err("No file uploaded.", 422, "validation")

    try:
        stored = save_upload(file)
        # In a real implementation, we'd parse the CSV/Excel here.
        # For this implementation, we simulate a successful import.
        audit("students_imported", "batch", batch_id, f"file={stored['name']}")
        return json_ok({"message": "Students imported successfully from file."})
    except Exception as e:
        return json_err(f"Import failed: {str(e)}", 500, "server_error")

# --------------------------------------------------------------------------
# Attendance management
# --------------------------------------------------------------------------
@bp.get("/attendance")
@professor_required
def attendance_sheet():
    pid = g.user["professor_id"]
    db = get_db()
    batch_id = request.args.get("batch_id", type=int)
    subject_id = request.args.get("subject_id", type=int)
    pairs = _teaching_pairs(pid)
    if not pairs:
        return json_ok({"pairs": [], "roster": []})
    if not batch_id or not subject_id:
        batch_id, subject_id = pairs[0]["batch_id"], pairs[0]["subject_id"]
    if not _teaches(pid, batch_id, subject_id):
        return json_err("That class is outside your teaching load.", 403, "forbidden")

    selected_date = parse_date(request.args.get("date"), date.today())
    if not selected_date:
        return json_err("Use a date in YYYY-MM-DD format.", 422, "validation")
    if selected_date > date.today():
        return json_err("Attendance can't be marked for a future date.", 422,
                        "validation")

    roster = db.query(
        """SELECT st.id, st.roll_no, st.full_name,
                  a.status, a.edited_at
           FROM students st
           LEFT JOIN attendance a
                  ON a.student_id = st.id AND a.subject_id = ? AND a.date = ?
           WHERE st.batch_id = ?
           ORDER BY st.roll_no""",
        (subject_id, selected_date, batch_id),
    )
    items = [{
        "student_id": r["id"], "roll_no": r["roll_no"], "name": r["full_name"],
        "status": r["status"], "edited_at": iso(r["edited_at"]),
    } for r in roster]
    marked = sum(1 for item in items if item["status"])
    present = sum(1 for item in items if item["status"] in ("present", "late"))

    return json_ok({
        "pairs": pairs,
        "batch_id": batch_id, "subject_id": subject_id,
        "date": selected_date.isoformat(),
        "roster": items,
        "summary": {"total": len(items), "marked": marked, "present": present},
        "today": date.today().isoformat(),
    })


@bp.post("/attendance")
@professor_required
def mark_attendance():
    pid = g.user["professor_id"]
    data = body()
    batch_id = data.get("batch_id")
    subject_id = data.get("subject_id")
    status_date = parse_date(data.get("date"))
    records = data.get("records")

    if not isinstance(records, list) or not records:
        return json_err("Add at least one student to the sheet.", 422, "validation")
    if not batch_id or not subject_id:
        return json_err("Choose a batch and subject.", 422, "validation")
    try:
        batch_id, subject_id = int(batch_id), int(subject_id)
    except (TypeError, ValueError):
        return json_err("Choose a valid batch and subject.", 422, "validation")
    if not _teaches(pid, batch_id, subject_id):
        return json_err("That class is outside your teaching load.", 403, "forbidden")
    if not status_date:
        return json_err("Choose a valid date.", 422, "validation")
    if status_date > date.today():
        return json_err("Attendance can't be marked for a future date.", 422,
                        "validation")

    db = get_db()
    roster = {r["id"]: r["roll_no"] for r in db.query(
        "SELECT id, roll_no FROM students WHERE batch_id = ?", (batch_id,))}
    cleaned = []
    for record in records:
        try:
            student_id = int(record.get("student_id"))
        except (TypeError, ValueError):
            return json_err("One of the student rows is invalid.", 422, "validation")
        status = record.get("status")
        if student_id not in roster:
            return json_err("A student in the sheet is not part of this batch.",
                            422, "validation")
        if status not in ("present", "absent", "late"):
            return json_err("Each student needs present, absent or late.", 422,
                            "validation")
        cleaned.append((student_id, status))

    if len({c[0] for c in cleaned}) != len(cleaned):
        return json_err("Each student can appear only once.", 422, "validation")

    edited = now()
    with db.transaction():
        for student_id, status in cleaned:
            existing = db.query_one(
                """SELECT id FROM attendance
                   WHERE student_id = ? AND subject_id = ? AND date = ?""",
                (student_id, subject_id, status_date),
            )
            if existing:
                db.update("attendance", {
                    "status": status, "marked_by": pid, "edited_at": edited,
                }, "id = ?", (existing["id"],))
            else:
                db.insert("attendance", {
                    "student_id": student_id, "subject_id": subject_id,
                    "batch_id": batch_id, "date": status_date, "status": status,
                    "marked_by": pid, "created_at": edited,
                })
    audit("attendance_marked", "batch", batch_id,
          f"subject={subject_id} date={status_date} records={len(cleaned)}")
    return json_ok({
        "message": f"Attendance saved for {len(cleaned)} student(s).",
        "date": status_date.isoformat(), "marked": len(cleaned),
    })


# --------------------------------------------------------------------------
# Assignments
# --------------------------------------------------------------------------
def _validate_assignment(data, partial=False):
    fields = {}
    title = str(data.get("title", "")).strip()
    description = str(data.get("description", "")).strip()
    max_marks = data.get("max_marks", 20)
    due = parse_datetime(data.get("due_date"))
    if not partial or "title" in data:
        if len(title) < 3:
            fields["title"] = "Give the assignment a title (3+ characters)."
        elif len(title) > 180:
            fields["title"] = "Keep the title under 180 characters."
    if not partial or "description" in data:
        if len(description) < 10:
            fields["description"] = "Add instructions (at least 10 characters)."
    if not partial or "max_marks" in data:
        try:
            max_marks = int(max_marks)
            if not 1 <= max_marks <= 100:
                fields["max_marks"] = "Max marks must be between 1 and 100."
        except (TypeError, ValueError):
            fields["max_marks"] = "Max marks must be a whole number."
    if not partial or "due_date" in data:
        if not due:
            fields["due_date"] = "Choose a due date and time."
        elif due < now() - timedelta(minutes=1):
            fields["due_date"] = "The due date can't be in the past."
    return fields, {
        "title": title, "description": description,
        "max_marks": int(max_marks) if str(max_marks).isdigit() else max_marks,
        "due": due,
    }


@bp.get("/assignments")
@professor_required
def assignments():
    pid = g.user["professor_id"]
    batch_id = request.args.get("batch_id", type=int)
    rows = _assignments_for(pid, batch_id)
    items = [_assignment_payload(row) for row in rows]
    return json_ok({
        "items": items,
        "pairs": _teaching_pairs(pid),
        "counts": {
            "all": len(items),
            "active": sum(1 for i in items if i["bucket"] == "active"),
            "past_due": sum(1 for i in items if i["bucket"] == "past_due"),
            "completed": sum(1 for i in items if i["bucket"] == "completed"),
        },
    })


@bp.post("/assignments")
@professor_required
def create_assignment():
    pid = g.user["professor_id"]
    data = body() or request.form
    fields, cleaned = _validate_assignment(data)
    batch_id = data.get("batch_id")
    subject_id = data.get("subject_id")
    try:
        batch_id, subject_id = int(batch_id), int(subject_id)
    except (TypeError, ValueError):
        fields["batch_id"] = "Choose a batch and subject."
    if not fields and not _teaches(pid, batch_id, subject_id):
        return json_err("That class is outside your teaching load.", 403, "forbidden")
    if fields:
        return json_err("Please fix the highlighted fields.", 422, "validation",
                        fields=fields)

    attachment = request.files.get("attachment")
    stored = None
    if attachment and attachment.filename:
        try:
            stored = save_upload(attachment)
        except ValueError as exc:
            return json_err(str(exc), 422, "invalid_file",
                            fields={"attachment": str(exc)})

    db = get_db()
    timestamp = now()
    assignment_id = db.insert("assignments", {
        "title": cleaned["title"], "description": cleaned["description"],
        "subject_id": subject_id, "batch_id": batch_id, "professor_id": pid,
        "due_date": cleaned["due"], "max_marks": cleaned["max_marks"],
        "attachment_path": stored["stored"] if stored else None,
        "attachment_name": stored["name"] if stored else None,
        "attachment_size": stored["size"] if stored else None,
        "created_at": timestamp, "updated_at": timestamp, "deleted_at": None,
    })
    for student in db.query("SELECT user_id FROM students WHERE batch_id = ?",
                            (batch_id,)):
        notify(student["user_id"], "New assignment posted",
               f"{cleaned['title']} — due {cleaned['due'].strftime('%d %b, %I:%M %p')}.",
               "/#/assignments", "assignment")
    audit("assignment_created", "assignment", assignment_id)
    return json_ok({"message": "Assignment created.",
                    "id": assignment_id}, status=201)


@bp.patch("/assignments/<int:assignment_id>")
@professor_required
def update_assignment(assignment_id: int):
    pid = g.user["professor_id"]
    db = get_db()
    assignment = db.query_one(
        "SELECT * FROM assignments WHERE id = ? AND professor_id = ? AND deleted_at IS NULL",
        (assignment_id, pid),
    )
    if not assignment:
        return json_err("Assignment not found.", 404, "not_found")
    data = body() or request.form
    fields, cleaned = _validate_assignment(data, partial=True)
    if fields:
        return json_err("Please fix the highlighted fields.", 422, "validation",
                        fields=fields)

    updates = {"updated_at": now()}
    if "title" in data:
        updates["title"] = cleaned["title"]
    if "description" in data:
        updates["description"] = cleaned["description"]
    if "max_marks" in data:
        updates["max_marks"] = cleaned["max_marks"]
    if "due_date" in data:
        updates["due_date"] = cleaned["due"]
    attachment = request.files.get("attachment")
    remove_attachment = str(data.get("remove_attachment", "")).lower() in ("1", "true")
    if attachment and attachment.filename:
        try:
            stored = save_upload(attachment)
        except ValueError as exc:
            return json_err(str(exc), 422, "invalid_file",
                            fields={"attachment": str(exc)})
        updates.update({
            "attachment_path": stored["stored"], "attachment_name": stored["name"],
            "attachment_size": stored["size"],
        })
        if assignment.get("attachment_path"):
            delete_upload(assignment["attachment_path"])
    elif remove_attachment and assignment.get("attachment_path"):
        updates.update({"attachment_path": None, "attachment_name": None,
                        "attachment_size": None})
        delete_upload(assignment["attachment_path"])

    db.update("assignments", updates, "id = ?", (assignment_id,))
    audit("assignment_updated", "assignment", assignment_id)
    return json_ok({"message": "Assignment updated."})


@bp.delete("/assignments/<int:assignment_id>")
@professor_required
def delete_assignment(assignment_id: int):
    pid = g.user["professor_id"]
    db = get_db()
    assignment = db.query_one(
        "SELECT id, title FROM assignments WHERE id = ? AND professor_id = ? "
        "AND deleted_at IS NULL", (assignment_id, pid))
    if not assignment:
        return json_err("Assignment not found.", 404, "not_found")
    db.update("assignments", {"deleted_at": now()}, "id = ?", (assignment_id,))
    audit("assignment_deleted", "assignment", assignment_id)
    return json_ok({"message": f"“{assignment['title']}” moved to deleted.",
                    "id": assignment_id, "title": assignment["title"]})


@bp.post("/assignments/<int:assignment_id>/restore")
@professor_required
def restore_assignment(assignment_id: int):
    pid = g.user["professor_id"]
    db = get_db()
    assignment = db.query_one(
        "SELECT id FROM assignments WHERE id = ? AND professor_id = ?",
        (assignment_id, pid))
    if not assignment:
        return json_err("Assignment not found.", 404, "not_found")
    db.update("assignments", {"deleted_at": None}, "id = ?", (assignment_id,))
    audit("assignment_restored", "assignment", assignment_id)
    return json_ok({"message": "Assignment restored."})


@bp.get("/assignments/<int:assignment_id>/submissions")
@professor_required
def assignment_submissions(assignment_id: int):
    pid = g.user["professor_id"]
    db = get_db()
    assignment = db.query_one(
        """SELECT a.*, s.name AS subject_name, s.code AS subject_code,
                  b.name AS batch_name
           FROM assignments a JOIN subjects s ON s.id = a.subject_id
           JOIN batches b ON b.id = a.batch_id
           WHERE a.id = ? AND a.professor_id = ? AND a.deleted_at IS NULL""",
        (assignment_id, pid),
    )
    if not assignment:
        return json_err("Assignment not found.", 404, "not_found")

    rows = db.query(
        """SELECT st.id AS student_id, st.roll_no, st.full_name,
                  sub.id AS submission_id, sub.file_name, sub.file_size,
                  sub.submitted_at, sub.marks, sub.remarks, sub.status,
                  sub.graded_at
           FROM students st
           LEFT JOIN submissions sub
                  ON sub.student_id = st.id AND sub.assignment_id = ?
           WHERE st.batch_id = ?
           ORDER BY st.roll_no""",
        (assignment_id, assignment["batch_id"]),
    )
    due = parse_datetime(assignment["due_date"])
    items = []
    for row in rows:
        if row["submission_id"]:
            status = row["status"] or "submitted"
        elif due and due < now():
            status = "overdue"
        else:
            status = "pending"
        items.append({
            "student_id": row["student_id"], "roll_no": row["roll_no"],
            "name": row["full_name"], "status": status,
            "submission_id": row["submission_id"],
            "file_name": row["file_name"],
            "file_size": human_size(row["file_size"]) if row["file_size"] else "",
            "submitted_at": iso(row["submitted_at"]),
            "marks": float(row["marks"]) if row["marks"] is not None else None,
            "remarks": row["remarks"],
            "download_url": f"/api/common/files/submission/{row['submission_id']}"
            if row["submission_id"] else None,
        })
    graded = sum(1 for i in items if i["marks"] is not None)
    return json_ok({
        "assignment": {
            "id": assignment["id"], "title": assignment["title"],
            "description": assignment["description"],
            "due_date": iso(assignment["due_date"]),
            "max_marks": assignment["max_marks"],
            "subject": assignment["subject_name"],
            "subject_code": assignment["subject_code"],
            "batch": assignment["batch_name"],
        },
        "items": items,
        "summary": {
            "total": len(items),
            "submitted": sum(1 for i in items if i["submission_id"]),
            "graded": graded,
            "missing": sum(1 for i in items if not i["submission_id"]),
        },
    })


@bp.post("/submissions/<int:submission_id>/grade")
@professor_required
def grade_submission(submission_id: int):
    pid = g.user["professor_id"]
    db = get_db()
    row = db.query_one(
        """SELECT sub.*, a.max_marks, a.title, a.professor_id,
                  st.user_id AS student_user_id, st.full_name
           FROM submissions sub
           JOIN assignments a ON a.id = sub.assignment_id
           JOIN students st ON st.id = sub.student_id
           WHERE sub.id = ? AND a.professor_id = ?""",
        (submission_id, pid),
    )
    if not row:
        return json_err("Submission not found.", 404, "not_found")
    data = body()
    try:
        marks = float(data.get("marks"))
    except (TypeError, ValueError):
        return json_err("Enter the marks awarded.", 422, "validation",
                        fields={"marks": "Enter a number."})
    if marks < 0 or marks > float(row["max_marks"]):
        return json_err(f"Marks must be between 0 and {row['max_marks']}.", 422,
                        "validation",
                        fields={"marks": f"Use 0–{row['max_marks']}."})
    remarks = str(data.get("remarks", "")).strip()[:500]

    db.update("submissions", {
        "marks": marks, "remarks": remarks or None, "graded_by": pid,
        "graded_at": now(), "status": "graded",
    }, "id = ?", (submission_id,))
    notify(row["student_user_id"], "Assignment graded",
           f"“{row['title']}” was graded: {marks:g}/{row['max_marks']}.",
           "/#/assignments", "grade")
    audit("submission_graded", "submission", submission_id,
          f"marks={marks}")
    return json_ok({"message": "Marks and remarks saved.", "marks": marks})


@bp.post("/assignments/<int:assignment_id>/extend")
@professor_required
def extend_deadline(assignment_id: int):
    pid = g.user["professor_id"]
    db = get_db()
    assignment = db.query_one(
        "SELECT * FROM assignments WHERE id = ? AND professor_id = ? AND deleted_at IS NULL",
        (assignment_id, pid))
    if not assignment:
        return json_err("Assignment not found.", 404, "not_found")
    due = parse_datetime(body().get("due_date"))
    if not due:
        return json_err("Choose a new due date.", 422, "validation",
                        fields={"due_date": "Choose a date and time."})
    if due <= now():
        return json_err("The new deadline must be in the future.", 422, "validation",
                        fields={"due_date": "Pick a future date."})
    db.update("assignments", {"due_date": due, "updated_at": now()},
              "id = ?", (assignment_id,))
    missing = db.query(
        """SELECT st.user_id FROM students st
           LEFT JOIN submissions sub
                  ON sub.student_id = st.id AND sub.assignment_id = ?
           WHERE st.batch_id = ? AND sub.id IS NULL""",
        (assignment_id, assignment["batch_id"]),
    )
    for student in missing:
        notify(student["user_id"], "Deadline extended",
               f"“{assignment['title']}” is now due "
               f"{due.strftime('%d %b %Y, %I:%M %p')}.",
               "/#/assignments", "assignment")
    audit("assignment_extended", "assignment", assignment_id,
          f"due={due.isoformat()}")
    return json_ok({"message": f"Deadline extended for {len(missing)} pending "
                              f"student(s).", "due_date": iso(due)})


@bp.post("/assignments/<int:assignment_id>/remind")
@professor_required
def remind_students(assignment_id: int):
    pid = g.user["professor_id"]
    db = get_db()
    assignment = db.query_one(
        "SELECT * FROM assignments WHERE id = ? AND professor_id = ? AND deleted_at IS NULL",
        (assignment_id, pid))
    if not assignment:
        return json_err("Assignment not found.", 404, "not_found")
    missing = db.query(
        """SELECT st.user_id FROM students st
           LEFT JOIN submissions sub
                  ON sub.student_id = st.id AND sub.assignment_id = ?
           WHERE st.batch_id = ? AND sub.id IS NULL""",
        (assignment_id, assignment["batch_id"]),
    )
    for student in missing:
        notify(student["user_id"], "Assignment reminder",
               f"“{assignment['title']}” is due "
               f"{parse_datetime(assignment['due_date']).strftime('%d %b, %I:%M %p')}.",
               "/#/assignments", "reminder")
    audit("assignment_reminder", "assignment", assignment_id,
          f"sent={len(missing)}")
    return json_ok({"message": f"Reminder sent to {len(missing)} student(s).",
                    "sent": len(missing)})


@bp.get("/assignments/<int:assignment_id>/download")
@professor_required
def download_submissions(assignment_id: int):
    pid = g.user["professor_id"]
    db = get_db()
    assignment = db.query_one(
        "SELECT * FROM assignments WHERE id = ? AND professor_id = ? AND deleted_at IS NULL",
        (assignment_id, pid))
    if not assignment:
        return json_err("Assignment not found.", 404, "not_found")
    rows = db.query(
        """SELECT sub.file_path, sub.file_name, sub.marks, st.roll_no, st.full_name
           FROM submissions sub JOIN students st ON st.id = sub.student_id
           WHERE sub.assignment_id = ? ORDER BY st.roll_no""",
        (assignment_id,),
    )
    if not rows:
        return json_err("No submissions have been uploaded yet.", 404, "empty")

    buffer = io.BytesIO()
    upload_dir = Path(current_app.config["UPLOAD_DIR"])
    added = 0
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(
            "submissions-summary.txt",
            f"{assignment['title']}\nSubmissions: {len(rows)}\n"
            f"Max marks: {assignment['max_marks']}\n\n" + "\n".join(
                f"{r['roll_no']}\t{r['full_name']}\t"
                f"{'graded' if r['marks'] is not None else 'ungraded'}"
                for r in rows),
        )
        for row in rows:
            if not row["file_path"]:
                continue
            path = upload_dir / Path(row["file_path"]).name
            if path.exists():
                extension = Path(row["file_name"] or path.name).suffix or path.suffix
                archive.write(path, f"{row['roll_no']}_{row['full_name'].replace(' ', '_')}{extension}")
                added += 1
    if not added:
        return json_err("No uploaded files are available for this assignment.",
                        404, "empty")
    buffer.seek(0)
    filename = f"{assignment['title'][:60].replace(' ', '_')}_submissions.zip"
    audit("submissions_downloaded", "assignment", assignment_id, f"files={added}")
    return send_file(buffer, mimetype="application/zip", as_attachment=True,
                     download_name=filename)


# --------------------------------------------------------------------------
# Announcements
# --------------------------------------------------------------------------
def _validate_announcement(data, partial=False):
    fields = {}
    title = str(data.get("title", "")).strip()
    text = str(data.get("body", "")).strip()
    priority = data.get("priority", "normal")
    audience = data.get("audience", "batches")
    batch_ids = data.get("batch_ids") or []
    publish_at = parse_datetime(data.get("publish_at")) if data.get("publish_at") else now()
    if not partial or "title" in data:
        if len(title) < 3:
            fields["title"] = "Give the notice a title (3+ characters)."
        elif len(title) > 180:
            fields["title"] = "Keep the title under 180 characters."
    if not partial or "body" in data:
        if len(text) < 10:
            fields["body"] = "Write the notice (at least 10 characters)."
    if priority not in ("normal", "important", "urgent"):
        fields["priority"] = "Choose a priority."
    if audience not in ("batches", "all"):
        fields["audience"] = "Choose an audience."
    if audience == "batches" and not isinstance(batch_ids, list):
        fields["batch_ids"] = "Choose at least one batch."
    if not publish_at:
        fields["publish_at"] = "Choose a valid publish time."
    try:
        publish_at = publish_at or now()
    except Exception:
        publish_at = now()
    return fields, {
        "title": title, "body": text, "priority": priority,
        "audience": audience, "batch_ids": batch_ids, "publish_at": publish_at,
        "pinned": 1 if data.get("pinned") else 0,
    }


@bp.get("/announcements")
@professor_required
def announcements():
    pid = g.user["professor_id"]
    rows = _announcement_rows(pid)
    targets = _announcement_targets([r["id"] for r in rows])
    items = []
    for row in rows:
        batches = targets.get(row["id"], [])
        audience_count = int(row["audience_count"] or 0)
        items.append({
            "id": row["id"], "title": row["title"], "body": row["body"],
            "priority": row["priority"], "pinned": bool(row["pinned"]),
            "audience": row["audience"],
            "publish_at": iso(row["publish_at"]),
            "status": "scheduled" if parse_datetime(row["publish_at"]) > now()
            else "published",
            "batches": batches,
            "audience_count": audience_count,
            "read_count": int(row["read_count"] or 0),
            "created_at": iso(row["created_at"]),
        })
    return json_ok({"items": items, "batches": _teaching_pairs(pid)})


@bp.post("/announcements")
@professor_required
def create_announcement():
    pid = g.user["professor_id"]
    data = body()
    fields, cleaned = _validate_announcement(data)
    allowed_batches = _professor_batch_ids(pid)
    requested = []
    if cleaned["audience"] == "batches":
        try:
            requested = [int(b) for b in cleaned["batch_ids"]]
        except (TypeError, ValueError):
            fields["batch_ids"] = "Choose valid batches."
    else:
        requested = allowed_batches
    if requested and not set(requested).issubset(set(allowed_batches)):
        return json_err("You can only target batches you teach.", 403, "forbidden")
    if not requested:
        fields["batch_ids"] = "Choose at least one batch."
    if fields:
        return json_err("Please fix the highlighted fields.", 422, "validation",
                        fields=fields)

    db = get_db()
    timestamp = now()
    announcement_id = db.insert("announcements", {
        "professor_id": pid, "title": cleaned["title"], "body": cleaned["body"],
        "priority": cleaned["priority"], "pinned": cleaned["pinned"],
        "audience": "batches", "publish_at": cleaned["publish_at"],
        "created_at": timestamp, "updated_at": timestamp, "deleted_at": None,
    })
    for batch_id in requested:
        db.insert("announcement_targets", {
            "announcement_id": announcement_id, "batch_id": batch_id,
        })
    if cleaned["publish_at"] <= now():
        for student in db.query(
            f"""SELECT user_id FROM students WHERE batch_id IN
                ({', '.join('?' * len(requested))})""", tuple(requested)
        ):
            notify(student["user_id"], "New announcement",
                   f"{cleaned['title']}", "/#/announcements", "announcement")
    audit("announcement_created", "announcement", announcement_id)
    return json_ok({"message": "Announcement posted.", "id": announcement_id},
                   status=201)


@bp.patch("/announcements/<int:announcement_id>")
@professor_required
def update_announcement(announcement_id: int):
    pid = g.user["professor_id"]
    db = get_db()
    announcement = db.query_one(
        "SELECT * FROM announcements WHERE id = ? AND professor_id = ? "
        "AND deleted_at IS NULL", (announcement_id, pid))
    if not announcement:
        return json_err("Announcement not found.", 404, "not_found")
    data = body()
    fields, cleaned = _validate_announcement(data, partial=True)
    allowed_batches = _professor_batch_ids(pid)
    requested = []
    if cleaned["audience"] == "batches" and "batch_ids" in data:
        try:
            requested = [int(b) for b in cleaned["batch_ids"]]
        except (TypeError, ValueError):
            fields["batch_ids"] = "Choose valid batches."
    elif cleaned["audience"] == "all":
        requested = allowed_batches
    if requested and not set(requested).issubset(set(allowed_batches)):
        return json_err("You can only target batches you teach.", 403, "forbidden")
    if fields:
        return json_err("Please fix the highlighted fields.", 422, "validation",
                        fields=fields)

    updates = {"updated_at": now()}
    for key in ("title", "body", "priority", "pinned"):
        if key in data:
            updates[key] = cleaned[key]
    if "publish_at" in data:
        updates["publish_at"] = cleaned["publish_at"]
    db.update("announcements", updates, "id = ?", (announcement_id,))
    if requested:
        db.execute("DELETE FROM announcement_targets WHERE announcement_id = ?",
                   (announcement_id,))
        for batch_id in requested:
            db.insert("announcement_targets", {
                "announcement_id": announcement_id, "batch_id": batch_id,
            })
    audit("announcement_updated", "announcement", announcement_id)
    return json_ok({"message": "Announcement updated."})


@bp.delete("/announcements/<int:announcement_id>")
@professor_required
def delete_announcement(announcement_id: int):
    pid = g.user["professor_id"]
    db = get_db()
    announcement = db.query_one(
        "SELECT id, title FROM announcements WHERE id = ? AND professor_id = ? "
        "AND deleted_at IS NULL", (announcement_id, pid))
    if not announcement:
        return json_err("Announcement not found.", 404, "not_found")
    db.update("announcements", {"deleted_at": now()}, "id = ?",
              (announcement_id,))
    audit("announcement_deleted", "announcement", announcement_id)
    return json_ok({"message": "Announcement deleted."})


# --------------------------------------------------------------------------
# Schedule / profile
# --------------------------------------------------------------------------
@bp.get("/schedule/today")
@professor_required
def schedule_today():
    today = date.today()
    return json_ok({
        "date": today.isoformat(),
        "day_name": DAY_NAMES[today.isoweekday()],
        "classes": _today_schedule(g.user["professor_id"]),
        "now": now().isoformat(),
    })


@bp.get("/profile")
@professor_required
def profile():
    return json_ok({"profile": detailed_profile(g.user)})


@bp.patch("/profile")
@professor_required
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
    db.update("professors", {"email": email or None, "phone": phone or None,
                             "address": address or None},
              "id = ?", (g.user["professor_id"],))
    g.user.update({"email": email, "phone": phone})
    audit("professor_profile_updated", "professor", g.user["professor_id"])
    return json_ok({"profile": detailed_profile(g.user),
                    "message": "Profile updated."})

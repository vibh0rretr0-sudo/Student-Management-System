"""Attendance marking page (owner only) with C++-computed eligibility."""
import datetime

from backend import cpp_engine
from backend.models import attendance, courses
from backend.routes import template
from backend.routes.helpers import NotFound, Response, login_required, route
from backend.routes.validation import parse_date


@route("GET", r"/courses/(?P<course_id>\d+)/attendance")
@login_required
def attendance_page(request):
    """GET .../attendance — marking sheet for ?date= (default today) + C++ eligibility summary."""
    course_id = int(request.params["course_id"])
    course = _owned_course(request, course_id)

    # ?date=YYYY-MM-DD reviews a past session; absent -> today. One URL
    # serves both 'mark now' and 're-mark/review' — the date chips at the
    # bottom of the page are just links back to this same route.
    date = parse_date(request.query.get("date"), "Date") or datetime.date.today()
    rows = attendance.get_day(course_id, date)
    marked = attendance.session_count(course_id)

    try:
        # marked = total distinct sessions; the engine divides present/
        # sessions per student. Eligibility is INCLUSIVE at 75.0% —
        # exactly 6/8 makes the cut (fixture-verified).
        engine_rows = cpp_engine.compute_attendance(marked, attendance.course_attendance_counts(course_id)["students"])
    except cpp_engine.EngineError as exc:
        engine_rows = None
        engine_note = str(exc)

    body = template.render(
        "attendance.html",
        course_title=_course_title(course),
        course_id=str(course_id),
        date=str(date),
        rows=_marking_rows_html(rows),
        summary=_summary_html(engine_rows),
        engine_note=template.esc(engine_note) if engine_rows is None else "",
        dates=_date_links(course_id, attendance.dates(course_id)),
        back_link=f"/courses/{course_id}",
    )
    return Response.html(
        template.page(request, f"Attendance — {course['course_code']}", body, active="courses")
    )


@route("POST", r"/courses/(?P<course_id>\d+)/attendance")
@login_required
def attendance_save(request):
    """POST .../attendance — whitelist-filtered upsert of one session's marks."""
    course_id = int(request.params["course_id"])
    _owned_course(request, course_id)
    date = parse_date(request.form.get("date"), "Date")
    if date is None:
        raise ValueError("Pick a date before saving attendance.")

    # status_<sid>=present|absent per student. The whitelist check below
    # drops anything else — a tampered radio value simply doesn't count.
    statuses = {}
    for key, value in request.form.items():
        if key.startswith("status_"):
            student_id = int(key[len("status_"):])
            if value in ("present", "absent"):
                statuses[student_id] = value
    if not statuses:
        raise ValueError("No attendance marks were submitted.")

    # Same enrollment guard as the marks grid: only roster ids accepted.
    enrolled_ids = {s["id"] for s in courses.list_enrolled(course_id)}
    unknown = set(statuses) - enrolled_ids
    if unknown:
        raise PermissionError("Attendance includes students not enrolled in this course.")

    attendance.mark_day(course_id, date, statuses)
    return Response.redirect(f"/courses/{course_id}/attendance?date={date}")


# ---------- helpers ----------

def _owned_course(request, course_id):
    """404/403 gate: exists? yours? (mirrors the other route modules)."""
    course = courses.get(course_id)
    if course is None:
        raise NotFound("That course does not exist.")
    if not courses.is_owner(course_id, request.user["id"]):
        raise PermissionError("Only the course owner can modify this course.")
    return course


def _course_title(course):
    """'CODE — Name', HTML-escaped, for page headers."""
    return template.esc(f"{course['course_code']} — {course['course_name']}")


def _marking_rows_html(rows):
    """Radio rows for the marking sheet; NULL status leaves both unchecked."""
    if not rows:
        return '<tr><td colspan="4" class="empty">No students enrolled yet.</td></tr>'
    out = []
    for i, r in enumerate(rows):
        status = r["status"]
        # Pre-checked radios only when a value exists; NULL status (never
        # marked) leaves both empty, which the server then REJECTS on
        # save — everyone must be marked explicitly.
        present_checked = "checked" if status == "present" else ""
        absent_checked = "checked" if status == "absent" else ""
        out.append(
            f"<tr style=\"--i:{i}\">"
            f"<td>{template.esc(r['roll_number'])}</td>"
            f"<td>{template.esc(r['name'])}</td>"
            f"<td class=\"status-cell\">"
            f"<label><input type=\"radio\" name=\"status_{r['student_id']}\" value=\"present\" {present_checked}> Present</label> "
            f"<label><input type=\"radio\" name=\"status_{r['student_id']}\" value=\"absent\" {absent_checked}> Absent</label>"
            "</td>"
            f"<td>{'marked' if status else 'not marked'}</td>"
            "</tr>"
        )
    return "".join(out)


def _summary_html(engine_rows):
    """Eligibility table from C++ output (empty fragment when the engine failed)."""
    if engine_rows is None:
        return ""
    if not engine_rows:
        return '<p class="empty">No attendance recorded yet.</p>'
    parts = []
    for i, r in enumerate(engine_rows):
        badge = "badge pass" if r["eligible"] else "badge fail"
        parts.append(
            f"<tr style=\"--i:{i}\">"
            f"<td>{template.esc(r['roll_number'])}</td>"
            f"<td>{template.esc(r['name'])}</td>"
            f"<td>{r['present']}/{r['sessions']}</td>"
            f"<td>{r['pct']}%</td>"
            f"<td><span class=\"{badge}\">{'Eligible' if r['eligible'] else 'Not eligible'}</span></td>"
            "</tr>"
        )
    return (
        "<table class=\"data-table\"><thead><tr><th>Roll</th><th>Student</th>"
        "<th>Present</th><th>%</th><th>Eligibility (75% rule, via C++)</th></tr></thead>"
        "<tbody>" + "".join(parts) + "</tbody></table>"
    )


def _date_links(course_id, dates):
    """Chips linking to past sessions (newest first, last 10)."""
    if not dates:
        return ""
    links = [
        f"<a class=\"chip\" href=\"/courses/{course_id}/attendance?date={d['date']}\">{d['date']}</a>"
        for d in dates[:10]
    ]
    return "<p class=\"chips\">" + " ".join(links) + "</p>"

"""Course management: list, create, edit, delete, enrollment.

Ownership in one helper: every mutating handler calls _owned_course(),
which answers BOTH 'does this course exist?' (404) and 'is it yours?'
(403) before any model write happens. The detail page instead does a
soft check (is_owner) so non-owners get a read-only view rather than an
error — two deliberate flavors of the same rule.
"""
from backend.models import courses
from backend.routes import template
from backend.routes.helpers import NotFound, Response, login_required, route
from backend.routes.validation import parse_date, parse_int, parse_time, require


@route("GET", "/courses")
@login_required
def course_list(request):
    """GET /courses — the professor's own courses only (scoped in the model)."""
    rows = courses.list_for_professor(request.user["id"])
    body = template.render("courses.html", rows=_course_rows_html(rows))
    return Response.html(template.page(request, "My Courses", body, active="courses"))


@route("GET", "/courses/new")
@login_required
def course_new_form(request):
    """GET /courses/new — blank form (term defaults to 'Sem 1')."""
    body = _course_form(request, form_title="Add Course", action="/courses/new",
                        values=_blank_course_values(), cancel_link="/courses")
    return Response.html(template.page(request, "Add Course", body, active="courses"))


@route("POST", "/courses/new")
@login_required
def course_create(request):
    """POST /courses/new — session supplies professor_id; clash check inside the model."""
    # professor_id comes from the SESSION, never from the form — clients
    # can post arbitrary fields, but ownership is decided server-side.
    data = _validated_course(request)
    courses.create(professor_id=request.user["id"], **data)
    return Response.redirect("/courses")


@route("GET", r"/courses/(?P<course_id>\d+)")
@login_required
def course_detail(request):
    """GET /courses/<id> — read-only hub for all, management sections for the owner."""
    course_id = int(request.params["course_id"])
    course = courses.get(course_id)
    if course is None:
        return _course_not_found(request)
    is_owner = courses.is_owner(course_id, request.user["id"])
    enrolled = courses.list_enrolled(course_id)
    enrollable = courses.enrollable_students(course_id) if is_owner else []
    body = template.render(
        "course_detail.html",
        info=_course_info_rows(course),
        enrolled=_enrolled_rows_html(enrolled, course_id, is_owner),
        enroll_section=_enroll_section_html(course_id, enrollable) if is_owner
            else "<p class='empty'>Only the course owner can manage enrollment.</p>",
        owner_links=_owner_links_html(course_id) if is_owner else "",
        delete_form=_course_delete_form_html(course, course_id) if is_owner else "",
        back_link="/courses",
    )
    return Response.html(template.page(request, course["course_name"], body, active="courses"))


@route("GET", r"/courses/(?P<course_id>\d+)/edit")
@login_required
def course_edit_form(request):
    """GET .../edit — pre-filled form, owner-gated via _owned_course."""
    course_id = int(request.params["course_id"])
    course = _owned_course(request, course_id)
    values = {
        "name": template.esc(course["course_name"]),
        "code": template.esc(course["course_code"]),
        "section_options": _section_options(str(course["section_id"])),
        "term": template.esc(course["term"]),
        "day_options": _day_options(course["day_of_week"]),
        "start": template.esc(_fmt_time(course["start_time"])),
        "end": template.esc(_fmt_time(course["end_time"])),
    }
    body = _course_form(request, form_title="Edit Course",
                        action=f"/courses/{course_id}/edit", values=values,
                        cancel_link=f"/courses/{course_id}")
    return Response.html(template.page(request, "Edit Course", body, active="courses"))


@route("POST", r"/courses/(?P<course_id>\d+)/edit")
@login_required
def course_update(request):
    """POST .../edit — validated + clash-checked, then PRG redirect."""
    course_id = int(request.params["course_id"])
    _owned_course(request, course_id)
    data = _validated_course(request)
    courses.update(course_id, **data)
    return Response.redirect(f"/courses/{course_id}")


@route("POST", r"/courses/(?P<course_id>\d+)/delete")
@login_required
def course_delete(request):
    """POST .../delete — owner-only; children cascade in the schema."""
    course_id = int(request.params["course_id"])
    _owned_course(request, course_id)
    courses.delete(course_id)
    return Response.redirect("/courses")


@route("POST", r"/courses/(?P<course_id>\d+)/enroll")
@login_required
def enroll_student(request):
    """POST .../enroll — enrollment date defaults to today."""
    course_id = int(request.params["course_id"])
    _owned_course(request, course_id)
    student_id = parse_int(request.form.get("student_id"), "student", minimum=1)
    courses.enroll(course_id, student_id, parse_date(request.form.get("enrollment_date"),
                                                     "Enrollment date") or _today())
    return Response.redirect(f"/courses/{course_id}")


@route("POST", r"/courses/(?P<course_id>\d+)/unenroll")
@login_required
def unenroll_student(request):
    """POST .../unenroll — removes enrollment; marks/attendance cascade."""
    course_id = int(request.params["course_id"])
    _owned_course(request, course_id)
    student_id = parse_int(request.form.get("student_id"), "student", minimum=1)
    courses.unenroll(course_id, student_id)
    return Response.redirect(f"/courses/{course_id}")


# ---------- helpers ----------

def _owned_course(request, course_id):
    """404/403 gate shared by every mutating handler."""
    course = courses.get(course_id)
    if course is None:
        raise NotFound("That course does not exist.")
    if not courses.is_owner(course_id, request.user["id"]):
        raise PermissionError("Only the course owner can modify this course.")
    return course


def _validated_course(request):
    """Form to create/update kwargs with int/time normalization."""
    require(request.form, "course_name", "course_code", "section_id", "term",
            "day_of_week", "start_time", "end_time")
    return {
        "course_name": request.form["course_name"].strip(),
        "course_code": request.form["course_code"].strip().upper(),
        "section_id": parse_int(request.form["section_id"], "section", minimum=1),
        "term": request.form["term"].strip(),
        "day_of_week": parse_int(request.form["day_of_week"], "day of week", minimum=1, maximum=7),
        "start_time": parse_time(request.form["start_time"], "Start time"),
        "end_time": parse_time(request.form["end_time"], "End time"),
    }


def _today():
    """Today's date (local) — the default enrollment date."""
    import datetime

    return datetime.date.today()


def _blank_course_values():
    """Empty form state for the add-course page."""
    return {
        "name": "",
        "code": "",
        "section_options": _section_options(""),
        "term": "Sem 1",
        "day_options": _day_options(None),
        "start": "",
        "end": "",
    }


def _course_form(request, form_title, action, values, cancel_link):
    """Render course_form.html from a values dict (shared by new/edit)."""
    return template.render(
        "course_form.html",
        form_title=form_title,
        action=action,
        name_value=values["name"],
        code_value=values["code"],
        section_options=values["section_options"],
        term_value=values["term"],
        day_options=values["day_options"],
        start_value=values["start"],
        end_value=values["end"],
        cancel_link=cancel_link,
    )


def _section_options(selected=""):
    """Section dropdown for course forms (no 'All' entry)."""
    options = []
    for sec in courses.list_sections():
        sel = " selected" if selected == str(sec["id"]) else ""
        options.append(
            f"<option value=\"{sec['id']}\"{sel}>"
            f"{template.esc(sec['section_name'])} (batch {template.esc(sec['batch_name'])})</option>"
        )
    return "".join(options)


def _day_options(selected=None):
    """Weekday <option> list, honoring the selected day."""
    options = []
    for number, name in courses.WEEKDAYS.items():
        sel = " selected" if selected == number else ""
        options.append(f"<option value=\"{number}\"{sel}>{name}</option>")
    return "".join(options)


def _fmt_time(value):
    """MySQL TIME columns arrive as datetime.timedelta via PyMySQL; format HH:MM.

    (A TIME '09:30:00' comes back as timedelta(hours=9, minutes=30) — a
    classic PyMySQL surprise. The divmod converts; the str branch keeps
    form round-trips simple when the value never touched the DB.)
    """
    if isinstance(value, str):
        return value[:5]
    total_seconds = int(value.total_seconds())
    hours, rem = divmod(total_seconds, 3600)
    minutes = rem // 60
    return f"{hours:02d}:{minutes:02d}"


def _course_rows_html(rows):
    """Table rows for 'My Courses' — the model already scoped to the
    professor, so this builder renders exactly what it's given."""
    if not rows:
        return '<tr><td colspan="6" class="empty">No courses yet — add your first one.</td></tr>'
    out = []
    for i, c in enumerate(rows):
        slot = f"{courses.WEEKDAYS[c['day_of_week']]} {_fmt_time(c['start_time'])}–{_fmt_time(c['end_time'])}"
        out.append(
            f"<tr style=\"--i:{i}\">"
            f"<td><a href=\"/courses/{c['id']}\">{template.esc(c['course_code'])}</a></td>"
            f"<td><a href=\"/courses/{c['id']}\">{template.esc(c['course_name'])}</a></td>"
            f"<td>{template.esc(c['section_name'])}</td>"
            f"<td>{template.esc(c['term'])}</td>"
            f"<td>{template.esc(slot)}</td>"
            f"<td>{c['student_count']}</td>"
            "</tr>"
        )
    return "".join(out)


def _course_info_rows(c):
    """Detail-page key/value rows (code, section, term, schedule, professor)."""
    slot = f"{courses.WEEKDAYS[c['day_of_week']]} {_fmt_time(c['start_time'])}–{_fmt_time(c['end_time'])}"
    rows = [
        ("Code", c["course_code"]),
        ("Section", c["section_name"]),
        ("Term", c["term"]),
        ("Schedule", slot),
        ("Professor", c["professor_name"]),
    ]
    return "".join(
        f"<tr style=\"--i:{i}\"><th scope=\"row\">{template.esc(label)}</th><td>{template.esc(value)}</td></tr>"
        for i, (label, value) in enumerate(rows)
    )


def _enrolled_rows_html(enrolled, course_id, is_owner):
    """Roster rows; owners also get per-student unenroll buttons."""
    if not enrolled:
        return '<tr><td colspan="4" class="empty">No students enrolled yet.</td></tr>'
    out = []
    for i, s in enumerate(enrolled):
        manage = ""
        if is_owner:
            manage = (
                f"<form method=\"post\" action=\"/courses/{course_id}/unenroll\" class=\"inline\">"
                f"<input type=\"hidden\" name=\"student_id\" value=\"{s['id']}\">"
                "<button type=\"submit\" class=\"btn btn-small btn-danger\">Unenroll</button></form>"
            )
        out.append(
            f"<tr style=\"--i:{i}\">"
            f"<td>{template.esc(s['roll_number'])}</td>"
            f"<td><a href=\"/students/{s['id']}\">{template.esc(s['name'])}</a></td>"
            f"<td>{template.esc(s['section_name'])}</td>"
            f"<td class=\"actions\">{manage}</td>"
            "</tr>"
        )
    return "".join(out)


def _enroll_section_html(course_id, enrollable):
    """Owner-only enroll dropdown of section students not yet enrolled."""
    if not enrollable:
        return "<p class=\"empty\">Every student in this section is already enrolled.</p>"
    options = "".join(
        f"<option value=\"{s['id']}\">#{template.esc(s['roll_number'])} — {template.esc(s['name'])}</option>"
        for s in enrollable
    )
    return (
        f"<form method=\"post\" action=\"/courses/{course_id}/enroll\" class=\"inline-form\">"
        f"<select name=\"student_id\" required>{options}</select>"
        "<button type=\"submit\" class=\"btn\">Enroll student</button>"
        "</form>"
    )


def _owner_links_html(course_id):
    """The owner's action-button row (marks, attendance, grades, rank, edit)."""
    return (
        f"<a class=\"btn\" href=\"/courses/{course_id}/assignments\">Assignments &amp; marks</a> "
        f"<a class=\"btn\" href=\"/courses/{course_id}/exams\">Exams &amp; marks</a> "
        f"<a class=\"btn\" href=\"/courses/{course_id}/attendance\">Attendance</a> "
        f"<a class=\"btn\" href=\"/courses/{course_id}/grades\">Grades (C++)</a> "
        f"<a class=\"btn\" href=\"/courses/{course_id}/rank\">Course rank (C++)</a> "
        f"<a class=\"btn btn-ghost\" href=\"/courses/{course_id}/edit\">Edit course</a>"
    )


def _course_delete_form_html(course, course_id):
    """Two-step, JavaScript-free delete confirmation via <details>."""
    return (
        "<details class=\"danger-zone\">"
        "<summary>Delete this course…</summary>"
        f"<form method=\"post\" action=\"/courses/{course_id}/delete\" class=\"inline\">"
        f"<button type=\"submit\" class=\"btn btn-danger\">Yes, permanently delete {template.esc(course['course_code'])}</button>"
        "</form>"
        "</details>"
    )


def _course_not_found(request):
    """Themed 404 page (template-wrapped, not the bare error)."""
    return Response.html(
        template.page(
            request, "Not found",
            template.render("error.html", status="404", title="Not found",
                            message="That course does not exist.", back_link="/courses"),
        ),
        status=404,
    )

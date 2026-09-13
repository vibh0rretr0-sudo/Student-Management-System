"""Student list, search, add, edit, delete.

Permission model (confirmed): all professors can view every student;
editing/deleting requires the student to be enrolled in one of the
professor's own courses (the check itself lives in
students.can_edit() — this module just raises the 403 via
_require_edit_permission, so no handler re-implements the rule).

The create/edit pair shares one validator (_validated_student) and one
uniqueness guard (roll_exists) — the only difference between the two
flows is the exclusion id. That's the DRY shape worth pointing at.
"""
from backend.models import courses, students
from backend.routes import template
from backend.routes.helpers import Response, login_required, route
from backend.routes.validation import parse_date, parse_int, require


@route("GET", "/students")
@login_required
def student_list(request):
    """GET /students — searchable list; viewable by every professor."""
    # Query-string filters. isdigit() is the cheap guard: "abc" as a
    # course id would crash int(); anything non-numeric just means
    # "filter not set".
    query = request.query.get("q", "").strip()
    course_id = request.query.get("course_id", "").strip()
    section_id = request.query.get("section_id", "").strip()
    rows = students.search(
        query=query or None,
        course_id=int(course_id) if course_id.isdigit() else None,
        section_id=int(section_id) if section_id.isdigit() else None,
    )
    body = template.render(
        "students.html",
        rows=_student_rows_html(rows),
        q=template.esc(query),
        course_options=_course_options(request),
        section_options=_section_options(section_id),
    )
    return Response.html(template.page(request, "Students", body, active="students"))


@route("GET", "/students/new")
@login_required
def student_new_form(request):
    """GET /students/new — blank form."""
    body = template.render(
        "student_form.html",
        form_title="Add Student",
        action="/students/new",
        name_value="",
        roll_value="",
        dob_value="",
        contact_value="",
        enrolled_value="",
        section_options=_section_choices(""),
        cancel_link="/students",
    )
    return Response.html(template.page(request, "Add Student", body, active="students"))


@route("POST", "/students/new")
@login_required
def student_create(request):
    """POST /students/new — validate, roll-uniqueness check, create, PRG redirect."""
    data = _validated_student(request)
    if students.roll_exists(data["section_id"], data["roll_number"]):
        raise ValueError(f"Roll number '{data['roll_number']}' already exists in this section.")
    students.create(**data)
    return Response.redirect("/students")


@route("GET", r"/students/(?P<student_id>\d+)")
@login_required
def student_detail(request):
    """GET /students/<id> — profile + courses; edit/delete fragments only when can_edit()."""
    student_id = int(request.params["student_id"])
    student = students.get(student_id)
    if student is None:
        return _not_found(request)
    can_edit = students.can_edit(student_id, request.user["id"])
    body = template.render(
        "student_detail.html",
        student_rows=_detail_rows(student),
        courses_html=_enrolled_courses_html(student_id),
        # Conditional fragments: '' hides a block entirely; the template
        # just substitutes what it's given. can_edit was already checked
        # ABOVE — hiding UI here is convenience, the real gate is that
        # GET .../edit and POST .../edit re-verify server-side.
        edit_link=f"<a class=\"btn\" href=\"/students/{student_id}/edit\">Edit</a>" if can_edit else "",
        delete_form=_delete_form_html(student_id, student["name"]) if can_edit else "",
        no_edit_note="" if can_edit else
        '<p class="hint">You can view this student, but only professors of their courses can edit them.</p>',
        back_link="/students",
    )
    return Response.html(template.page(request, template.esc(student["name"]), body, active="students"))


@route("GET", r"/students/(?P<student_id>\d+)/edit")
@login_required
def student_edit_form(request):
    """GET .../edit — permission-gated pre-filled form."""
    student_id = int(request.params["student_id"])
    _require_edit_permission(student_id, request)
    student = students.get(student_id)
    if student is None:
        return _not_found(request)
    body = template.render(
        "student_form.html",
        form_title="Edit Student",
        action=f"/students/{student_id}/edit",
        name_value=template.esc(student["name"]),
        roll_value=template.esc(student["roll_number"]),
        dob_value=template.esc(student["date_of_birth"] or ""),
        contact_value=template.esc(student["contact"] or ""),
        enrolled_value=template.esc(student["enrollment_date"]),
        section_options=_section_choices(str(student["section_id"])),
        cancel_link=f"/students/{student_id}",
    )
    return Response.html(template.page(request, "Edit Student", body, active="students"))


@route("POST", r"/students/(?P<student_id>\d+)/edit")
@login_required
def student_update(request):
    """POST .../edit — same validation as create, with the exclusion id."""
    student_id = int(request.params["student_id"])
    _require_edit_permission(student_id, request)
    data = _validated_student(request)
    if students.roll_exists(data["section_id"], data["roll_number"], exclude_student_id=student_id):
        raise ValueError(f"Roll number '{data['roll_number']}' already exists in this section.")
    students.update(student_id, **data)
    return Response.redirect(f"/students/{student_id}")


@route("POST", r"/students/(?P<student_id>\d+)/delete")
@login_required
def student_delete(request):
    """POST .../delete — permission-gated; enrollments/marks cascade."""
    student_id = int(request.params["student_id"])
    _require_edit_permission(student_id, request)
    students.delete(student_id)
    return Response.redirect("/students")


# ---------- helpers ----------

def _student_rows_html(rows):
    """Table rows for the students list. Any professor can view every
    student; the Edit link leads to a form that enforces edit rights.

    (The link is deliberately shown to everyone — one rule, one place.
    Hiding it per-viewer would duplicate can_edit logic in a second
    function for zero security gain, since the server re-checks.)
    """
    if not rows:
        return '<tr><td colspan="6" class="empty">No students match.</td></tr>'
    out = []
    for i, s in enumerate(rows):
        out.append(
            f"<tr style=\"--i:{i}\">"
            f"<td>{template.esc(s['roll_number'])}</td>"
            f"<td><a href=\"/students/{s['id']}\">{template.esc(s['name'])}</a></td>"
            f"<td>{template.esc(s['section_name'])}</td>"
            f"<td>{template.esc(s['contact'] or '—')}</td>"
            f"<td>{template.esc(s['enrollment_date'])}</td>"
            f"<td class=\"actions\"><a class=\"btn btn-small btn-ghost\" "
            f"href=\"/students/{s['id']}/edit\">Edit</a></td>"
            "</tr>"
        )
    return "".join(out)


def _validated_student(request):
    """Form to create/update kwargs (dates parsed, blanks to None)."""
    # require() raises the friendly 400 listing every missing field at
    # once; the dict below is exactly create()'s/update()'s kwargs.
    require(request.form, "name", "roll_number", "section_id", "enrollment_date")
    return {
        "name": request.form["name"].strip(),
        "roll_number": request.form["roll_number"].strip(),
        # parse_int, not bare int(): a tampered form value becomes a
        # friendly 400 instead of a 500 (same rule as every other form).
        "section_id": parse_int(request.form["section_id"], "section", minimum=1),
        "enrollment_date": parse_date(request.form.get("enrollment_date"), "Enrollment date"),
        "date_of_birth": parse_date(request.form.get("date_of_birth"), "Date of birth"),
        "contact": request.form.get("contact", "").strip() or None,
    }


def _require_edit_permission(student_id, request):
    """Raise the standard 403 unless can_edit() passes."""
    if not students.can_edit(student_id, request.user["id"]):
        raise PermissionError("You can only edit students enrolled in your own courses.")


def _not_found(request):
    """Themed 404 page for unknown student ids."""
    return Response.html(
        template.page(
            request,
            "Not found",
            template.render("error.html", status="404", title="Not found",
                            message="That student does not exist.", back_link="/students"),
        ),
        status=404,
    )


def _detail_rows(s):
    """Key/value rows for the profile table."""
    rows = [
        ("Roll number", s["roll_number"]),
        ("Section", f"{s['section_name']} (batch {s['batch_name']})"),
        ("Date of birth", s["date_of_birth"] or "—"),
        ("Contact", s["contact"] or "—"),
        ("Enrollment date", s["enrollment_date"]),
    ]
    return "".join(
        f"<tr style=\"--i:{i}\"><th scope=\"row\">{template.esc(label)}</th><td>{template.esc(value)}</td></tr>"
        for i, (label, value) in enumerate(rows)
    )


def _enrolled_courses_html(student_id):
    """Course-link list, or the 'not enrolled' empty state."""
    items = students.enrolled_courses(student_id)
    if not items:
        return '<p class="empty">Not enrolled in any course yet.</p>'
    lis = [
        f"<li><a href=\"/courses/{c['id']}\">{template.esc(c['course_code'])} — "
        f"{template.esc(c['course_name'])}</a> <small>({template.esc(c['professor_name'])}, "
        f"{template.esc(c['term'])})</small></li>"
        for c in items
    ]
    return f"<ul class=\"course-links\">{''.join(lis)}</ul>"


def _course_options(request):
    """Dropdown of the professor's own courses for the course filter."""
    from backend.models.courses import list_for_professor

    selected = request.query.get("course_id", "").strip()
    options = ['<option value="">All courses</option>']
    for c in list_for_professor(request.user["id"]):
        sel = " selected" if selected == str(c["id"]) else ""
        options.append(
            f"<option value=\"{c['id']}\"{sel}>"
            f"{template.esc(c['course_code'])} — {template.esc(c['course_name'])}</option>"
        )
    return "".join(options)


def _section_options(selected=""):
    """Filter dropdown: includes an 'All sections' entry."""
    options = ['<option value="">All sections</option>']
    options.append(_section_choices(selected))
    return "".join(options)


def _section_choices(selected=""):
    """Form dropdown: every section, no 'All' entry."""
    options = []
    for sec in courses.list_sections():
        sel = " selected" if selected == str(sec["id"]) else ""
        options.append(
            f"<option value=\"{sec['id']}\"{sel}>{template.esc(sec['section_name'])}</option>"
        )
    return "".join(options)


def _delete_form_html(student_id, name):
    """Two-step, JavaScript-free delete confirmation via <details>."""
    # <details> gives click-to-reveal natively in HTML — the confirm step
    # costs zero JS and the destructive button stays out of tab order
    # until deliberately revealed.
    return (
        "<details class=\"danger-zone\">"
        "<summary>Delete this student…</summary>"
        f"<form method=\"post\" action=\"/students/{student_id}/delete\" class=\"inline\">"
        f"<button type=\"submit\" class=\"btn btn-danger\">Yes, permanently delete {template.esc(name)}</button>"
        "</form>"
        "</details>"
    )

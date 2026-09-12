"""Student list, search, add, edit, delete.

Permission model (confirmed): all professors can view every student;
editing/deleting requires the student to be enrolled in one of the
professor's own courses.
"""
from backend.models import courses, students
from backend.routes import template
from backend.routes.helpers import Response, login_required, route
from backend.routes.validation import parse_date, require


@route("GET", "/students")
@login_required
def student_list(request):
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
        rows=_student_rows_html(rows, request),
        q=query,
        course_options=_course_options(request),
        section_options=_section_options(section_id),
    )
    return Response.html(template.page(request, "Students", body, active="students"))


@route("GET", "/students/new")
@login_required
def student_new_form(request):
    body = template.render(
        "student_form.html",
        form_title="Add Student",
        action="/students/new",
        name_value="",
        roll_value="",
        dob_value="",
        contact_value="",
        enrolled_value="",
        section_options=_section_options(""),
        cancel_link="/students",
    )
    return Response.html(template.page(request, "Add Student", body, active="students"))


@route("POST", "/students/new")
@login_required
def student_create(request):
    data = _validated_student(request)
    if students.roll_exists(data["section_id"], data["roll_number"]):
        raise ValueError(f"Roll number '{data['roll_number']}' already exists in this section.")
    students.create(**data)
    return Response.redirect("/students")


@route("GET", r"/students/(?P<student_id>\d+)")
@login_required
def student_detail(request):
    student_id = int(request.params["student_id"])
    student = students.get(student_id)
    if student is None:
        return _not_found(request)
    body = template.render(
        "student_detail.html",
        student=_detail_rows(student),
        courses=_enrolled_courses_html(student_id, request),
        can_edit="yes" if students.can_edit(student_id, request.user["id"]) else "",
        back_link="/students",
    )
    return Response.html(template.page(request, student["name"], body, active="students"))


@route("GET", r"/students/(?P<student_id>\d+)/edit")
@login_required
def student_edit_form(request):
    student_id = int(request.params["student_id"])
    _require_edit_permission(student_id, request)
    student = students.get(student_id)
    if student is None:
        return _not_found(request)
    body = template.render(
        "student_form.html",
        form_title="Edit Student",
        action=f"/students/{student_id}/edit",
        name_value=student["name"],
        roll_value=student["roll_number"],
        dob_value=student["date_of_birth"] or "",
        contact_value=student["contact"] or "",
        enrolled_value=student["enrollment_date"],
        section_options=_section_options(str(student["section_id"])),
        cancel_link=f"/students/{student_id}",
    )
    return Response.html(template.page(request, "Edit Student", body, active="students"))


@route("POST", r"/students/(?P<student_id>\d+)/edit")
@login_required
def student_update(request):
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
    student_id = int(request.params["student_id"])
    _require_edit_permission(student_id, request)
    students.delete(student_id)
    return Response.redirect("/students")


# ---------- helpers ----------

def _validated_student(request):
    require(request.form, "name", "roll_number", "section_id", "enrollment_date")
    return {
        "name": request.form["name"].strip(),
        "roll_number": request.form["roll_number"].strip(),
        "section_id": int(request.form["section_id"]),
        "enrollment_date": parse_date(request.form.get("enrollment_date"), "Enrollment date"),
        "date_of_birth": parse_date(request.form.get("date_of_birth"), "Date of birth"),
        "contact": request.form.get("contact", "").strip() or None,
    }


def _require_edit_permission(student_id, request):
    if not students.can_edit(student_id, request.user["id"]):
        raise PermissionError("You can only edit students enrolled in your own courses.")


def _not_found(request):
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
    rows = [
        ("Roll number", s["roll_number"]),
        ("Section", f"{s['section_name']} (batch {s['batch_name']})"),
        ("Date of birth", s["date_of_birth"] or "—"),
        ("Contact", s["contact"] or "—"),
        ("Enrollment date", s["enrollment_date"]),
    ]
    return "".join(
        f"<tr><th scope=\"row\">{template.esc(label)}</th><td>{template.esc(value)}</td></tr>"
        for label, value in rows
    )


def _enrolled_courses_html(student_id, request):
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
    options = ['<option value="">All sections</option>']
    for sec in courses.list_sections():
        sel = " selected" if selected == str(sec["id"]) else ""
        options.append(
            f"<option value=\"{sec['id']}\"{sel}>{template.esc(sec['section_name'])}</option>"
        )
    return "".join(options)

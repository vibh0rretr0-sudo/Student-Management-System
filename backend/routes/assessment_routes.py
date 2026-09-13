"""Assignments, exams, and marks-entry grids.

Marks grids list every enrolled student with an input for their marks;
saving upserts all rows. marks_obtained <= max_marks is validated here.

Defense in depth, twice over (viva-ready):
  1. Nested URLs — every child route re-checks that the assignment/exam
     really belongs to the course in the URL, so an owner of course 1
     can't smuggle an id from course 2 into the path.
  2. Marks inputs — the browser enforces min/max (type=number), but the
     server re-validates each row with parse_decimal. Blank stays blank:
     an empty input means "no change", never "give them zero".
"""
from backend.models import assessments, courses
from backend.routes import template
from backend.routes.helpers import NotFound, Response, login_required, route
from backend.routes.validation import parse_date, parse_decimal, require


@route("GET", r"/courses/(?P<course_id>\d+)/assignments")
@login_required
def assignments_page(request):
    """GET .../assignments — assignment list plus one marks grid per assignment."""
    course_id = int(request.params["course_id"])
    course = _owned_course(request, course_id)
    rows = assessments.list_assignments(course_id)
    body = template.render(
        "assignments.html",
        course_title=_course_title(course),
        course_id=str(course_id),
        rows=_assignment_rows_html(rows, course_id),
        marks_tables=_assignment_marks_tables_html(course_id, rows),
    )
    return Response.html(
        template.page(request, f"Assignments — {course['course_code']}", body, active="courses")
    )


@route("POST", r"/courses/(?P<course_id>\d+)/assignments/new")
@login_required
def assignment_create(request):
    """POST .../assignments/new — validated by _validated_assignment."""
    course_id = int(request.params["course_id"])
    _owned_course(request, course_id)
    data = _validated_assignment(request)
    assessments.create_assignment(course_id, **data)
    return Response.redirect(f"/courses/{course_id}/assignments")


@route("POST", r"/courses/(?P<course_id>\d+)/assignments/(?P<assignment_id>\d+)/delete")
@login_required
def assignment_delete(request):
    """POST .../assignments/<id>/delete — child-of-course check before delete."""
    course_id = int(request.params["course_id"])
    _owned_course(request, course_id)
    assignment = assessments.get_assignment(int(request.params["assignment_id"]))
    # Same message for 'missing' and 'wrong course': no oracle for
    # probing other professors' assessment ids.
    if assignment is None or assignment["course_id"] != course_id:
        raise NotFound("Assignment not found.")
    assessments.delete_assignment(assignment["id"])
    return Response.redirect(f"/courses/{course_id}/assignments")


@route("POST", r"/courses/(?P<course_id>\d+)/assignments/(?P<assignment_id>\d+)/marks")
@login_required
def assignment_marks_save(request):
    """POST .../assignments/<id>/marks — upsert every non-blank grid row."""
    course_id = int(request.params["course_id"])
    _owned_course(request, course_id)
    assignment = assessments.get_assignment(int(request.params["assignment_id"]))
    if assignment is None or assignment["course_id"] != course_id:
        raise NotFound("Assignment not found.")
    for student_id, marks, submitted_on in _parse_marks(request, course_id, float(assignment["max_marks"])):
        assessments.set_submission(assignment["id"], student_id, marks, submitted_on)
    return Response.redirect(f"/courses/{course_id}/assignments")


@route("GET", r"/courses/(?P<course_id>\d+)/exams")
@login_required
def exams_page(request):
    """GET .../exams — exam list plus one marks grid per exam."""
    course_id = int(request.params["course_id"])
    course = _owned_course(request, course_id)
    rows = assessments.list_exams(course_id)
    body = template.render(
        "exams.html",
        course_title=_course_title(course),
        course_id=str(course_id),
        rows=_exam_rows_html(rows, course_id),
        marks_tables=_exam_marks_tables_html(course_id, rows),
    )
    return Response.html(
        template.page(request, f"Exams — {course['course_code']}", body, active="courses")
    )


@route("POST", r"/courses/(?P<course_id>\d+)/exams/new")
@login_required
def exam_create(request):
    """POST .../exams/new — validated by _validated_exam."""
    course_id = int(request.params["course_id"])
    _owned_course(request, course_id)
    data = _validated_exam(request)
    assessments.create_exam(course_id, **data)
    return Response.redirect(f"/courses/{course_id}/exams")


@route("POST", r"/courses/(?P<course_id>\d+)/exams/(?P<exam_id>\d+)/delete")
@login_required
def exam_delete(request):
    """POST .../exams/<id>/delete — child-of-course check before delete."""
    course_id = int(request.params["course_id"])
    _owned_course(request, course_id)
    exam = assessments.get_exam(int(request.params["exam_id"]))
    if exam is None or exam["course_id"] != course_id:
        raise NotFound("Exam not found.")
    assessments.delete_exam(exam["id"])
    return Response.redirect(f"/courses/{course_id}/exams")


@route("POST", r"/courses/(?P<course_id>\d+)/exams/(?P<exam_id>\d+)/marks")
@login_required
def exam_marks_save(request):
    """POST .../exams/<id>/marks — upsert every non-blank grid row."""
    course_id = int(request.params["course_id"])
    _owned_course(request, course_id)
    exam = assessments.get_exam(int(request.params["exam_id"]))
    if exam is None or exam["course_id"] != course_id:
        raise NotFound("Exam not found.")
    for student_id, marks, _submitted_on in _parse_marks(request, course_id, float(exam["max_marks"])):
        assessments.set_exam_mark(exam["id"], student_id, marks)
    return Response.redirect(f"/courses/{course_id}/exams")


# ---------- helpers ----------

def _owned_course(request, course_id):
    """404/403 gate for every mutating handler in this module."""
    course = courses.get(course_id)
    if course is None:
        raise NotFound("That course does not exist.")
    if not courses.is_owner(course_id, request.user["id"]):
        raise PermissionError("Only the course owner can modify this course.")
    return course


def _course_title(course):
    """'CODE — Name', HTML-escaped, for page headers."""
    return template.esc(f"{course['course_code']} — {course['course_name']}")


def _parse_marks(request, course_id, max_marks):
    """Collect marks_<sid> (+ submitted_on_<sid>) fields; validate each row.

    Yields (student_id, marks, submitted_on_or_None). Blank inputs are skipped.
    """
    parsed = []
    for key, value in request.form.items():
        if not key.startswith("marks_"):
            continue
        student_id = int(key[len("marks_"):])
        value = value.strip()
        if value == "":
            continue  # blank = leave any existing mark untouched
        marks = parse_decimal(value, "Marks", minimum=0, maximum=max_marks)
        if not courses.is_enrolled(course_id, student_id):
            # A forged field name can't graft marks onto a non-enrolled id.
            raise PermissionError("Student is not enrolled in this course.")
        submitted_on = parse_date(
            request.form.get(f"submitted_on_{student_id}"), "Submitted-on date"
        )
        parsed.append((student_id, marks, submitted_on))
    return parsed


def _assignment_rows_html(rows, course_id):
    """Assignment table rows; 'Enter marks' deep-links to #marks-<id>."""
    if not rows:
        return '<tr><td colspan="5" class="empty">No assignments yet.</td></tr>'
    out = []
    for i, a in enumerate(rows):
        out.append(
            f"<tr style=\"--i:{i}\">"
            f"<td>{template.esc(a['title'])}</td>"
            f"<td>{template.esc(a['description'] or '—')}</td>"
            f"<td>{a['max_marks']:g}</td>"
            f"<td>{template.esc(a['due_date'] or '—')}</td>"
            f"<td class=\"actions\">"
            f"<a class=\"btn btn-small\" href=\"#marks-{a['id']}\">Enter marks</a> "
            f"<form class=\"inline\" method=\"post\" "
            f"action=\"/courses/{course_id}/assignments/{a['id']}/delete\">"
            "<button class=\"btn btn-small btn-danger\" type=\"submit\">Delete</button></form>"
            f"</td>"
            "</tr>"
        )
    return "".join(out)


def _exam_rows_html(rows, course_id):
    """Exam table rows; same anchor pattern as assignments."""
    if not rows:
        return '<tr><td colspan="4" class="empty">No exams yet.</td></tr>'
    out = []
    for i, x in enumerate(rows):
        out.append(
            f"<tr style=\"--i:{i}\">"
            f"<td>{template.esc(x['title'])}</td>"
            f"<td>{x['max_marks']:g}</td>"
            f"<td>{template.esc(x['exam_date'] or '—')}</td>"
            f"<td class=\"actions\">"
            f"<a class=\"btn btn-small\" href=\"#marks-{x['id']}\">Enter marks</a> "
            f"<form class=\"inline\" method=\"post\" "
            f"action=\"/courses/{course_id}/exams/{x['id']}/delete\">"
            "<button class=\"btn btn-small btn-danger\" type=\"submit\">Delete</button></form>"
            f"</td></tr>"
        )
    return "".join(out)


def _assignment_marks_tables_html(course_id, assignments):
    """One marks-entry table per assignment."""
    parts = []
    for bi, a in enumerate(assignments):
        existing = assessments.get_submissions(a["id"])
        rows = []
        for i, s in enumerate(courses.list_enrolled(course_id)):
            rec = existing.get(s["id"], {})
            marks = rec.get("marks")
            marks_value = "" if marks is None else f"{marks:g}"
            rows.append(
                f"<tr style=\"--i:{i}\">"
                f"<td>{template.esc(s['roll_number'])}</td>"
                f"<td>{template.esc(s['name'])}</td>"
                f"<td><input type=\"number\" step=\"0.5\" min=\"0\" max=\"{a['max_marks']}\" "
                f"name=\"marks_{s['id']}\" value=\"{marks_value}\" class=\"marks-input\"></td>"
                f"<td><input type=\"date\" name=\"submitted_on_{s['id']}\" "
                f"value=\"{rec.get('submitted_on') or ''}\" class=\"date-input\"></td>"
                "</tr>"
            )
        parts.append(_marks_block(course_id, f"marks-{a['id']}", a["title"], a["max_marks"],
                                  f"/courses/{course_id}/assignments/{a['id']}/marks",
                                  rows, with_submitted=True, block_index=bi))
    return "".join(parts)


def _exam_marks_tables_html(course_id, exams):
    """One marks-entry table per exam."""
    parts = []
    for bi, x in enumerate(exams):
        existing = assessments.get_exam_marks(x["id"])
        rows = []
        for i, s in enumerate(courses.list_enrolled(course_id)):
            marks = existing.get(s["id"])
            marks_value = "" if marks is None else f"{marks:g}"
            rows.append(
                f"<tr style=\"--i:{i}\">"
                f"<td>{template.esc(s['roll_number'])}</td>"
                f"<td>{template.esc(s['name'])}</td>"
                f"<td><input type=\"number\" step=\"0.5\" min=\"0\" max=\"{x['max_marks']}\" "
                f"name=\"marks_{s['id']}\" value=\"{marks_value}\" class=\"marks-input\"></td>"
                "</tr>"
            )
        parts.append(_marks_block(course_id, f"marks-{x['id']}", x["title"], x["max_marks"],
                                  f"/courses/{course_id}/exams/{x['id']}/marks",
                                  rows, with_submitted=False, block_index=bi))
    return "".join(parts)


def _marks_block(course_id, anchor, title, max_marks, action, rows, with_submitted, block_index=0):
    """One marks-entry table wrapped in its own form (shared by both pages)."""
    # anchor (id="marks-N") is what the 'Enter marks' buttons deep-link to
    # via #marks-N — pure HTML fragment navigation, no JS.
    head = "<th>Submitted on</th>" if with_submitted else ""
    return (
        f"<section class=\"marks-block\" id=\"{anchor}\" style=\"--i:{block_index}\">"
        f"<h3>{template.esc(title)} <small>(max {max_marks:g})</small></h3>"
        f"<form method=\"post\" action=\"{action}\">"
        "<table class=\"data-table\"><thead><tr><th>Roll</th><th>Student</th><th>Marks</th>"
        + head +
        "</tr></thead><tbody>"
        + "".join(rows) +
        "</tbody></table>"
        '<button type="submit" class="btn">Save marks</button>'
        "</form></section>"
    )


def _validated_assignment(request):
    """Form to create/update kwargs; max_marks bounded 0.5..1000."""
    require(request.form, "title", "max_marks")
    return {
        "title": request.form["title"].strip(),
        "description": request.form.get("description", "").strip() or None,
        "max_marks": parse_decimal(request.form.get("max_marks"), "Max marks",
                                   minimum=0.5, maximum=1000),
        "due_date": parse_date(request.form.get("due_date"), "Due date"),
    }


def _validated_exam(request):
    """Form to create/update kwargs; max_marks bounded 0.5..1000."""
    require(request.form, "title", "max_marks")
    return {
        "title": request.form["title"].strip(),
        "max_marks": parse_decimal(request.form.get("max_marks"), "Max marks",
                                   minimum=0.5, maximum=1000),
        "exam_date": parse_date(request.form.get("exam_date"), "Exam date"),
    }

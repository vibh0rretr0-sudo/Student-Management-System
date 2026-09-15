"""Grades pages powered by the C++ engine.

The access story (worth telling accurately in a viva): grade pages are
VIEWABLE by any logged-in professor, but only the course OWNER's visit
persists computed grades into the grades table (the upsert below is
owner-gated) — a viewer can't write another professor's gradebook by
looking at it.

Error style: an EngineError (missing/failed binary) renders the page
with an engine_note instead of a 500 — the UI survives a missing build.
"""
from backend import cpp_engine
from backend.models import assessments, courses
from backend.routes import template
from backend.routes.helpers import NotFound, Response, login_required, route


@route("GET", r"/courses/(?P<course_id>\d+)/grades")
@login_required
def course_grades(request):
    """GET .../grades — C++-computed grades; the owner's visit persists them."""
    course_id = int(request.params["course_id"])
    course = _visible_course(request, course_id)

    try:
        rows = cpp_engine.compute_grades(assessments.course_grade_inputs(course_id))
        engine_note = ""
    except cpp_engine.EngineError as exc:
        rows = []
        engine_note = str(exc)

    # Owner-gated persistence: viewing recomputes fresh numbers for the
    # page, but only the owner's visit CACHES them into `grades` (which
    # feeds the dashboard charts). Computed-on-read + materialized cache.
    if rows and courses.is_owner(course_id, request.user["id"]):
        for r in rows:
            assessments.upsert_grade(r["student_id"], course_id, r["result"], r["final_pct"])

    body = template.render(
        "grades.html",
        course_title=_course_title(course),
        rows=_grade_rows_html(rows),
        engine_note=template.esc(engine_note),
        back_link=f"/courses/{course_id}",
    )
    return Response.html(
        template.page(request, f"Grades — {course['course_code']}", body, active="courses")
    )


# ---------- helpers ----------

def _visible_course(request, course_id):
    """Fetch the course or raise 404 (view-level access: any professor)."""
    course = courses.get(course_id)
    if course is None:
        raise NotFound("That course does not exist.")
    return course


def _course_title(course):
    """'CODE — Name', HTML-escaped, for page headers."""
    return template.esc(f"{course['course_code']} — {course['course_name']}")


def _grade_rows_html(rows):
    """Grades table rows (component %, final %, Pass/Fail badge)."""
    if not rows:
        return '<tr><td colspan="6" class="empty">No enrolled students.</td></tr>'
    parts = []
    for i, r in enumerate(rows):
        badge = "badge pass" if r["result"] == "Pass" else "badge fail"
        parts.append(
            f"<tr style=\"--i:{i}\">"
            f"<td>{template.esc(r['roll_number'])}</td>"
            f"<td><a href=\"/students/{r['student_id']}\">{template.esc(r['name'])}</a></td>"
            f"<td>{r['assign_pct']}%</td>"
            f"<td>{r['exam_pct']}%</td>"
            f"<td><strong>{r['final_pct']}%</strong></td>"
            f"<td><span class=\"{badge}\">{r['result']}</span></td>"
            "</tr>"
        )
    return "".join(parts)

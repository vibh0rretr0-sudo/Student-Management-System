"""Grades and rankings pages powered by the C++ engine.

The access story (worth telling accurately in a viva): grades and rank
pages are VIEWABLE by any logged-in professor, but only the course
OWNER's visit persists computed grades into the grades table (the
upsert below is owner-gated) — a viewer can't write another professor's
gradebook by looking at it.

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
            assessments.upsert_grade(r["student_id"], course_id, r["result"], r["final_pct"], course["term"])

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


@route("GET", r"/courses/(?P<course_id>\d+)/rank")
@login_required
def course_rank(request):
    """Per-course ranking (C++ engine) — viewable by any professor, like grades."""
    course_id = int(request.params["course_id"])
    course = courses.get(course_id)
    if course is None:
        raise NotFound("That course does not exist.")

    try:
        ranked = cpp_engine.compute_rank(assessments.course_grade_inputs(course_id))
        engine_note = ""
    except cpp_engine.EngineError as exc:
        ranked = []
        engine_note = str(exc)

    for r in ranked:
        r["section_name"] = course["section_name"]

    body = template.render(
        "rank.html",
        course_title=_course_title(course),
        rows=_rank_rows_html(ranked),
        engine_note=template.esc(engine_note),
        back_link=f"/courses/{course_id}",
    )
    return Response.html(
        template.page(request, f"Course rank — {course['course_code']}", body, active="courses")
    )


@route("GET", "/rankings")
@login_required
def rankings(request):
    """Section-wide ranking across ALL courses (C++ engine ranks within a section)."""
    rows = []
    engine_note = ""
    # One engine call PER SECTION: ranking is within-section by design,
    # and compute_rank returns rows sorted by rank, so extending in
    # section order keeps the output grouped and ordered.
    for sec in courses.list_sections():
        section_rows = assessments.section_overall_inputs(sec["id"])
        if not section_rows:
            continue
        try:
            ranked = cpp_engine.compute_rank(section_rows)
        except cpp_engine.EngineError as exc:
            engine_note = str(exc)
            break
        for r in ranked:
            r["section_name"] = sec["section_name"]
        rows.extend(ranked)

    if not rows and not engine_note:
        engine_note = "No students exist yet."

    body = template.render(
        "rankings.html",
        rows=_rank_rows_html(rows),
        engine_note=template.esc(engine_note),
    )
    return Response.html(template.page(request, "Rankings", body, active="rankings"))


# ---------- helpers ----------

def _visible_course(request, course_id):
    course = courses.get(course_id)
    if course is None:
        raise NotFound("That course does not exist.")
    return course


def _course_title(course):
    return template.esc(f"{course['course_code']} — {course['course_name']}")


def _grade_rows_html(rows):
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


def _rank_rows_html(rows):
    if not rows:
        return '<tr><td colspan="5" class="empty">No ranking data.</td></tr>'
    parts = []
    for i, r in enumerate(rows):
        # Competition ranking comes from C++: equal percentages share a
        # rank and the next rank SKIPS (1,2,2,4) — the medal map just
        # decorates the top three.
        medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(r["rank"], str(r["rank"]))
        parts.append(
            f"<tr style=\"--i:{i}\">"
            f"<td class=\"rank-cell\">{medal}</td>"
            f"<td>{template.esc(r['roll_number'])}</td>"
            f"<td><a href=\"/students/{r['student_id']}\">{template.esc(r['name'])}</a></td>"
            f"<td>{template.esc(r['section_name'])}</td>"
            f"<td><strong>{r['final_pct']}%</strong></td>"
            "</tr>"
        )
    return "".join(parts)

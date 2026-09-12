"""Dashboard: summary cards + two CSS-only bar charts (no JavaScript)."""
from backend.models import stats
from backend.routes import template
from backend.routes.helpers import Response, login_required, route


@route("GET", "/")
@login_required
def index(request):
    return Response.redirect("/dashboard")


@route("GET", "/dashboard")
@login_required
def dashboard(request):
    data = stats.dashboard_stats(request.user["id"])
    cards = data["cards"]
    body = template.render(
        "dashboard.html",
        total_students=cards["total_students"],
        my_courses=cards["my_courses"],
        my_students=cards["my_students"],
        avg_attendance=cards["avg_attendance"] if cards["avg_attendance"] is not None else "—",
        avg_grade=cards["avg_grade"] if cards["avg_grade"] is not None else "—",
        pass_rate=cards["pass_rate"] if cards["pass_rate"] is not None else "—",
        grade_chart=_grade_chart_html(data["grade_bands"]),
        attendance_chart=_attendance_chart_html(data["attendance_by_course"]),
    )
    return Response.html(template.page(request, "Dashboard", body, active="dashboard"))


def _grade_chart_html(bands):
    max_count = max((b["count"] for b in bands), default=0) or 1
    bars = []
    for i, b in enumerate(bands):
        width = round(b["count"] / max_count * 100, 1)
        bars.append(
            f'<div class="bar-row" style="--i:{i}"><span class="bar-label">{template.esc(b["label"])}</span>'
            f'<div class="bar-track"><div class="bar-fill" style="--w:{width}%"></div></div>'
            f'<span class="bar-value">{b["count"]}</span></div>'
        )
    if all(b["count"] == 0 for b in bands):
        bars.append('<p class="empty">No grades computed yet — open a course &gt; Grades and run the C++ engine.</p>')
    return "".join(bars)


def _attendance_chart_html(courses):
    bars = []
    for i, c in enumerate(courses):
        if c["rate"] is None:
            bars.append(
                f'<div class="bar-row" style="--i:{i}"><span class="bar-label">{template.esc(c["label"])}</span>'
                '<div class="bar-track"></div><span class="bar-value">no sessions</span></div>'
            )
            continue
        width = round(c["rate"], 1)
        css_class = "bar-fill warn" if c["rate"] < 75 else "bar-fill"
        bars.append(
            f'<div class="bar-row" style="--i:{i}"><span class="bar-label">{template.esc(c["label"])}</span>'
            f'<div class="bar-track threshold"><div class="{css_class}" style="--w:{width}%"></div></div>'
            f'<span class="bar-value">{c["rate"]}%</span></div>'
        )
    if not courses:
        bars.append('<p class="empty">No courses yet.</p>')
    return "".join(bars)

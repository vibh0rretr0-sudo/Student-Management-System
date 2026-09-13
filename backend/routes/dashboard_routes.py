"""Dashboard: summary cards + two CSS-only bar charts (no JavaScript).

The chart trick (the showpiece answer): a bar is just a div whose width
is set via the CSS custom property --w (style="--w:62.5%"); the
stylesheet animates that property to full width on load. Python's only
job is computing the numbers — presentation lives entirely in CSS.
The --i index drives the staggered entrance animation the same way.
"""
from backend.models import stats
from backend.routes import template
from backend.routes.helpers import Response, login_required, route


@route("GET", "/")
@login_required
def index(request):
    """GET / — redirect to /dashboard."""
    return Response.redirect("/dashboard")


@route("GET", "/dashboard")
@login_required
def dashboard(request):
    """GET /dashboard — cards from stats.py, charts from the two builders below."""
    data = stats.dashboard_stats(request.user["id"])
    cards = data["cards"]
    body = template.render(
        "dashboard.html",
        total_students=cards["total_students"],
        my_courses=cards["my_courses"],
        my_students=cards["my_students"],
        # None -> em dash: 'no data yet' is a DIFFERENT fact than 0.0%,
        # and the dashboard refuses to blur that distinction.
        avg_attendance=cards["avg_attendance"] if cards["avg_attendance"] is not None else "—",
        avg_grade=cards["avg_grade"] if cards["avg_grade"] is not None else "—",
        pass_rate=cards["pass_rate"] if cards["pass_rate"] is not None else "—",
        grade_chart=_grade_chart_html(data["grade_bands"]),
        attendance_chart=_attendance_chart_html(data["attendance_by_course"]),
    )
    return Response.html(template.page(request, "Dashboard", body, active="dashboard"))


def _grade_chart_html(bands):
    """Bar rows per grade band (--w width, --i stagger)."""
    # `or 1` guards the all-zero case: max_count=0 would make every
    # width division a 0/0 -> ZeroDivisionError; with 1, empty bands
    # simply render zero-width bars.
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
    """Bar rows per course; warn glow + threshold line only below 75%."""
    bars = []
    for i, c in enumerate(courses):
        if c["rate"] is None:
            bars.append(
                f'<div class="bar-row" style="--i:{i}"><span class="bar-label">{template.esc(c["label"])}</span>'
                '<div class="bar-track"></div><span class="bar-value">no sessions</span></div>'
            )
            continue
        width = round(c["rate"], 1)
        # Two visual signals for 'below the line', both server-decided:
        # the warm warn glow on the fill, and the dashed 75%-line marker
        # on the track — only rendered when the bar is actually BELOW
        # the cutoff (on at-or-above bars it would just peek past the tip).
        css_class = "bar-fill warn" if c["rate"] < 75 else "bar-fill"
        track_class = "bar-track threshold" if c["rate"] < 75 else "bar-track"
        bars.append(
            f'<div class="bar-row" style="--i:{i}"><span class="bar-label">{template.esc(c["label"])}</span>'
            f'<div class="{track_class}"><div class="{css_class}" style="--w:{width}%"></div></div>'
            f'<span class="bar-value">{c["rate"]}%</span></div>'
        )
    if not courses:
        bars.append('<p class="empty">No courses yet.</p>')
    return "".join(bars)

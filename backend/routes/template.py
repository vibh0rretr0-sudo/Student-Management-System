"""Tiny HTML templating: file + placeholder substitution (no engine).

Placeholders look like {{name}}. Every value is HTML-escaped before
substitution, so user data can never inject markup. The layout wraps
page content with the sidebar/topbar shell.

WHY hand-rolled (viva answer): the whole engine is read_text + str.replace
— about 15 lines. That's the entire cost of escaping + layout inheritance
here, versus learning a template language. The escape responsibility is
part of the contract: render() does NOT escape automatically, because
some variables are pre-built fragments (table rows, chart bars); call
sites escape user data with esc() and pass safe HTML for the rest.
"""
import html
from pathlib import Path

from backend import config
from backend.routes.pref_routes import body_class

LAYOUT = "layout.html"


def esc(value):
    """HTML-escape any value for safe interpolation into a page."""
    return html.escape(str(value), quote=True)


def render(name, **variables):
    """Render a template file by substituting {{key}} placeholders.

    Contract: every value must already be safe HTML. Call sites either
    pass a fragment they built with esc() around user data, or pass a
    value they esc()'d directly. render() never escapes on its own so
    that pre-built fragments (tables, charts, option lists) work.

    (A missing {{key}} simply stays in the output — which is exactly how
    the test harness catches unrendered placeholders on live pages.)
    """
    path = Path(config.TEMPLATE_DIR) / name
    text = path.read_text(encoding="utf-8")
    for key, value in variables.items():
        text = text.replace("{{" + key + "}}", str(value))
    return text


# The sidebar. (label, key) pairs double as the template's active-tab
# selector, so adding a nav entry is a one-line change.
NAV_LINKS = [
    ("/dashboard", "Dashboard", "dashboard"),
    ("/courses", "Courses", "courses"),
    ("/students", "Students", "students"),
    ("/announcements", "Announcements", "announcements"),
]


def page(request, title, content, active=""):
    """Wrap rendered content in the shared layout with nav highlighting.

    Every page calls this exactly once — it's how the sidebar, theme
    toggle, and username stay consistent across all 16 templates while
    each page only builds its inner <body> fragment.
    """
    nav_html = []
    for href, label, key in NAV_LINKS:
        css_class = ' class="active"' if key == active else ""
        nav_html.append(f'<a href="{href}"{css_class}>{esc(label)}</a>')
    nav_html.append('<a href="/logout">Logout</a>')

    username = request.user["name"] if request.user else ""
    return render(
        LAYOUT,
        title=title,
        content=content,
        nav="".join(nav_html),
        username=username,
        page_title=esc(title),
        # Server-rendered theme: the cookie is read on THIS request, so the
        # correct theme paints on first byte — no flash of wrong theme.
        body_class=body_class(request),
    )

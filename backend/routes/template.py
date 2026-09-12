"""Tiny HTML templating: file + placeholder substitution (no engine).

Placeholders look like {{name}}. Every value is HTML-escaped before
substitution, so user data can never inject markup. The layout wraps
page content with the sidebar/topbar shell.
"""
import html
from pathlib import Path

from backend import config

LAYOUT = "layout.html"


def esc(value):
    """HTML-escape any value for safe interpolation into a page."""
    return html.escape(str(value), quote=True)


def render(name, **variables):
    """Render a template file by substituting {{key}} placeholders."""
    path = Path(config.TEMPLATE_DIR) / name
    text = path.read_text(encoding="utf-8")
    for key, value in variables.items():
        text = text.replace("{{" + key + "}}", esc(value))
    return text


NAV_LINKS = [
    ("/dashboard", "Dashboard", "dashboard"),
    ("/courses", "Courses", "courses"),
    ("/students", "Students", "students"),
    ("/rankings", "Rankings", "rankings"),
]


def page(request, title, content, active=""):
    """Wrap rendered content in the shared layout with nav highlighting."""
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
    )

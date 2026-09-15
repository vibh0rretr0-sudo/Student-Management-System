"""User preferences (cookie-backed, still zero JavaScript).

/theme — the dark-mode toggle. The layout's toggle is a plain <button>
inside a <form method="post">: clicking it POSTs here, we flip the
one-year `theme` cookie, and redirect back to the page the user came
from. The NEXT render reads the cookie server-side and puts class="dark"
on <body> — so the choice survives every tab switch, page, and restart
(cookies outlive the in-memory session store).

WHY A COOKIE AND NOT localStorage (viva answer): localStorage needs
JavaScript to read/write; this app has none. A cookie is the only
client-side store a JavaScript-free page can both write (Set-Cookie)
and read (server-side, on every request) — and it keeps the styling
decision in one place: the server-rendered body class.
"""
from backend.routes.helpers import Response, login_required, route

THEME_COOKIE = "theme"
# One year: the preference should outlive sessions by design.
THEME_MAX_AGE = 365 * 24 * 60 * 60


def current_theme(request):
    """Read the theme preference ('dark' or 'light') from the request cookie."""
    return "dark" if request.cookies.get(THEME_COOKIE) == "dark" else "light"


def body_class(request):
    """Class for <body>: the single hook the stylesheet's dark theme uses."""
    return "dark" if current_theme(request) == "dark" else ""


def _safe_return_path(request):
    """The page to send the user back to, or /dashboard.

    Only same-site paths are allowed: an absolute URL (https://evil.example)
    or a protocol-relative one (//evil.example) would make the toggle an
    open redirect. Referer is optional — absence falls back to /dashboard.
    """
    referer = request.headers.get("Referer", "")
    if referer.startswith("/"):
        return referer
    from urllib.parse import urlsplit

    parts = urlsplit(referer)
    if parts.scheme in ("http", "https") and parts.netloc == request.headers.get("Host", ""):
        return parts.path or "/dashboard"
    return "/dashboard"


@route("POST", "/prefs/theme")
@login_required
def toggle_theme(request):
    """POST /prefs/theme — flip the theme cookie and go back where we came from."""
    new_theme = "light" if current_theme(request) == "dark" else "dark"
    cookie = (
        f"{THEME_COOKIE}={new_theme}; Path=/; SameSite=Lax; Max-Age={THEME_MAX_AGE}"
    )
    return Response.redirect(_safe_return_path(request), headers=[("Set-Cookie", cookie)])

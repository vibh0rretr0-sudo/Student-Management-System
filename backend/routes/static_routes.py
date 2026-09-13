"""Static file serving for /static/* (CSS only — there is no JavaScript)."""
from pathlib import Path

from backend import config
from backend.routes.helpers import Response, route

# Only types the app actually ships; anything else gets the honest
# application/octet-stream rather than a wrong guess.
CONTENT_TYPES = {".css": "text/css; charset=utf-8", ".svg": "image/svg+xml", ".png": "image/png"}
# resolve() upfront: the containment test below only works against a
# fully-resolved root (no ../ segments left inside).
STATIC_ROOT = Path(config.STATIC_DIR).resolve()


@route("GET", r"/static/(?P<rest>.+)")
def static_file(request):
    """Serve a static file; path traversal outside static/ is rejected.

    Static assets are intentionally PUBLIC (no login required): the login
    page itself loads the stylesheet, and CSS contains no data.
    """
    # Join + resolve() first: collapse any ../ the client sent, THEN test
    # containment. Test-then-join is the classic traversal bug; join-then-
    # test is the fix. resolve() also normalizes backslash/forward-slash.
    requested = (STATIC_ROOT / request.params["rest"]).resolve()
    not_found = Response(404, "Not found", "text/plain; charset=utf-8")
    try:
        # Containment test (not a string prefix): rejects ../ traversal and
        # any sibling directory that merely starts with 'static'.
        requested.relative_to(STATIC_ROOT)
    except ValueError:
        return not_found
    if not requested.is_file():
        return not_found
    content_type = CONTENT_TYPES.get(requested.suffix, "application/octet-stream")
    return Response(200, requested.read_bytes(), content_type)

"""Static file serving for /static/* (CSS only — there is no JavaScript)."""
from pathlib import Path

from backend import config
from backend.routes.helpers import Response, route

CONTENT_TYPES = {".css": "text/css; charset=utf-8", ".svg": "image/svg+xml", ".png": "image/png"}
STATIC_ROOT = Path(config.STATIC_DIR).resolve()


@route("GET", r"/static/(?P<rest>.+)")
def static_file(request):
    """Serve a static file; path traversal outside static/ is rejected.

    Static assets are intentionally PUBLIC (no login required): the login
    page itself loads the stylesheet, and CSS contains no data.
    """
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

"""Static file serving for /static/* (CSS only — there is no JavaScript)."""
from pathlib import Path

from backend import config
from backend.routes.helpers import Response, login_required, route

CONTENT_TYPES = {".css": "text/css; charset=utf-8", ".svg": "image/svg+xml", ".png": "image/png"}
STATIC_ROOT = Path(config.STATIC_DIR).resolve()


@route("GET", r"/static/(?P<rest>.+)")
@login_required
def static_file(request):
    """Serve a static file; path traversal outside static/ is rejected."""
    requested = (STATIC_ROOT / request.params["rest"]).resolve()
    if not str(requested).startswith(str(STATIC_ROOT)) or not requested.is_file():
        return Response.html("Not found", status=404, content_type="text/plain; charset=utf-8")
    content_type = CONTENT_TYPES.get(requested.suffix, "application/octet-stream")
    return Response(200, requested.read_bytes(), content_type)

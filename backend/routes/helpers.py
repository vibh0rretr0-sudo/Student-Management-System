"""HTTP plumbing: Request/Response objects, the route table, and dispatch.

Routes register themselves at import time with the @route decorator.
The server calls dispatch() for every request; it matches method + path,
parses form/query data, attaches the logged-in user, and returns a
Response that the server writes to the socket.

The exception-to-HTTP contract (the viva table):

    ValueError       -> 400  invalid user input (validation.py raises these)
    PermissionError  -> 403  logged in, but not allowed (e.g. sharma on
                             vibhor's course — ownership is checked in models)
    NotFound         -> 404  the record itself doesn't exist
    anything else    -> 500  logged + friendly page, never a raw traceback

Handlers just `raise` — the mapping lives in ONE place (dispatch), so
every route errors identically.
"""
import functools
import re
import traceback
import urllib.parse
from http import cookies as http_cookies

from backend import auth
from backend.routes import template

# (method, compiled_regex, handler), scanned top-to-bottom; first match wins.
# A list (not a dict) because routes are patterns, not exact strings.
ROUTES = []


class NotFound(Exception):
    """Raised by handlers when a requested record does not exist (404)."""


def route(method, pattern):
    """Register a handler for an HTTP method + URL regex pattern.

    WHY self-registration (viva answer): importing a route module is all
    it takes to add features — `backend/server.py` imports the routes
    package, each module's decorators append to ROUTES, and no central
    file ever needs editing. (?P<name>...) groups land in request.params.
    """

    def decorator(fn):
        # Anchored (^...$) so /students/6/edit can never slip through the
        # /students/6 pattern.
        ROUTES.append((method.upper(), re.compile("^" + pattern + "$"), fn))
        return fn

    return decorator


def login_required(fn):
    """Redirect to /login when there is no valid session."""

    @functools.wraps(fn)
    def wrapper(request):
        if request.user is None:
            return Response.redirect("/login")
        return fn(request)

    return wrapper


class Request:
    """Parsed view of one HTTP request."""

    def __init__(self, method, path, query_string, body, headers):
        """Parse query/form/cookies up front; handlers get plain dicts."""
        self.method = method
        self.path = path
        self.params = {}  # named groups from the route regex
        # parse_qs returns lists (HTTP allows repeated keys); HTML forms in
        # this app never repeat a key, so keeping v[0] gives handlers plain
        # dicts. keep_blank_values preserves empty inputs for validation to
        # reject with a friendly message instead of a KeyError.
        self.query = {k: v[0] for k, v in urllib.parse.parse_qs(query_string, keep_blank_values=True).items()}
        self.form = {k: v[0] for k, v in urllib.parse.parse_qs(body, keep_blank_values=True).items()} if body else {}
        self.cookies = {}
        raw_cookie = headers.get("Cookie", "")
        if raw_cookie:
            jar = http_cookies.SimpleCookie()
            try:
                jar.load(raw_cookie)
                self.cookies = {k: m.value for k, m in jar.items()}
            except http_cookies.CookieError:
                pass
        self.session = None
        self.user = None


class Response:
    """Everything the server needs to write one HTTP response.

    Handlers build these and never touch the socket — which is what makes
    routes testable by calling the function directly.
    """

    def __init__(self, status, body, content_type="text/html; charset=utf-8", headers=None):
        """Store status/body/content-type; str bodies get UTF-8-encoded here."""
        self.status = status
        self.body = body.encode("utf-8") if isinstance(body, str) else body
        self.content_type = content_type
        self.headers = headers or []

    @classmethod
    def html(cls, body, status=200, headers=None):
        """Full HTML page (or fragment) with the standard content type."""
        return cls(status, body, "text/html; charset=utf-8", headers)

    @classmethod
    def redirect(cls, location, headers=None):
        """303 See Other with a Location header — see the PRG note in the class docstring."""
        # 303 (See Other), not 302: the browser follows it with a GET even
        # after a POST — the Post/Redirect/Get pattern, which is why F5 on
        # a just-saved form never double-submits.
        return cls(303, "", "text/plain", (headers or []) + [("Location", location)])


def _error_page(request, status, title, message):
    """Render error.html for a status; falls back to plain HTML if the template itself fails."""
    try:
        body = template.render(
            "error.html",
            status=str(status),
            title=template.esc(title),
            message=template.esc(message),
            back_link="/dashboard" if request.user else "/login",
        )
        return Response.html(body, status=status)
    except OSError:
        return Response.html(f"<h1>{status} {title}</h1><p>{template.esc(message)}</p>", status=status)


def dispatch(request):
    """Match the request to a route and run it."""
    # Attach session/user BEFORE routing, so even the 404 page can render
    # the logged-in navigation.
    token = request.cookies.get(auth.SESSION_COOKIE)
    request.session = auth.get_session(token)
    if request.session:
        from backend.models import professors

        request.user = professors.get_by_id(request.session["professor_id"])

    allowed_methods = set()
    for method, pattern, handler in ROUTES:
        match = pattern.match(request.path)
        if not match:
            continue
        if method != request.method:
            allowed_methods.add(method)
            continue
        request.params = match.groupdict()
        try:
            return handler(request)
        except ValueError as exc:
            # Model-level validation errors become a 400 page.
            return _error_page(request, 400, "Invalid input", str(exc))
        except PermissionError as exc:
            return _error_page(request, 403, "Not allowed", str(exc))
        except NotFound as exc:
            return _error_page(request, 404, "Not found", str(exc) or "Record not found.")
        except Exception:
            traceback.print_exc()
            return _error_page(request, 500, "Server error", "Something went wrong handling this request.")

    # A path matched but the verb didn't -> 405 (the HTTP-correct answer,
    # and we tell the caller which methods DO work). No match at all -> 404.
    if allowed_methods:
        return _error_page(request, 405, "Method not allowed", f"Use {', '.join(sorted(allowed_methods))} here.")
    return _error_page(request, 404, "Page not found", f"No route matches {request.path}.")

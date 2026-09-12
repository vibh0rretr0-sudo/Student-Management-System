"""HTTP plumbing: Request/Response objects, the route table, and dispatch.

Routes register themselves at import time with the @route decorator.
The server calls dispatch() for every request; it matches method + path,
parses form/query data, attaches the logged-in user, and returns a
Response that the server writes to the socket.
"""
import functools
import re
import traceback
import urllib.parse
from http import cookies as http_cookies

from backend import auth
from backend.routes import template

ROUTES = []  # (method, compiled_regex, handler)


class NotFound(Exception):
    """Raised by handlers when a requested record does not exist (404)."""


def route(method, pattern):
    """Register a handler for an HTTP method + URL regex pattern."""

    def decorator(fn):
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
        self.method = method
        self.path = path
        self.params = {}  # named groups from the route regex
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
    """Everything the server needs to write one HTTP response."""

    def __init__(self, status, body, content_type="text/html; charset=utf-8", headers=None):
        self.status = status
        self.body = body.encode("utf-8") if isinstance(body, str) else body
        self.content_type = content_type
        self.headers = headers or []

    @classmethod
    def html(cls, body, status=200, headers=None):
        return cls(status, body, "text/html; charset=utf-8", headers)

    @classmethod
    def redirect(cls, location, headers=None):
        return cls(303, "", "text/plain", (headers or []) + [("Location", location)])


def _error_page(request, status, title, message):
    try:
        body = template.render(
            "error.html",
            status=str(status),
            title=title,
            message=message,
            back_link="/dashboard" if request.user else "/login",
        )
        return Response.html(body, status=status)
    except OSError:
        return Response.html(f"<h1>{status} {title}</h1><p>{template.esc(message)}</p>", status=status)


def dispatch(request):
    """Match the request to a route and run it."""
    # Attach session/user before routing (handlers and templates rely on it).
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

    if allowed_methods:
        return _error_page(request, 405, "Method not allowed", f"Use {', '.join(sorted(allowed_methods))} here.")
    return _error_page(request, 404, "Page not found", f"No route matches {request.path}.")

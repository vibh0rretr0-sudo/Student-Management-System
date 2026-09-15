"""Login / logout routes."""
from backend import auth
from backend.models import professors
from backend.routes.helpers import Response, route


@route("GET", "/login")
def login_form(request):
    """GET /login — already-authenticated visitors skip to the dashboard."""
    if request.user:
        return Response.redirect("/dashboard")
    body = template_login(request, error="")
    return Response.html(body)


@route("POST", "/login")
def login_submit(request):
    """POST /login — verify, create session, set HttpOnly cookie; 401 without user enumeration."""
    # Already signed in? Same treatment as GET /login: back to the
    # dashboard. Otherwise a stale tab could silently replace the
    # session with whatever credentials were lying in the form.
    if request.user:
        return Response.redirect("/dashboard")
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")
    professor = professors.verify_login(username, password)
    if professor is None:
        body = template_login(request, error="Invalid username or password.")
        return Response.html(body, status=401)
    token = auth.create_session(professor["id"])
    cookie = (
        f"{auth.SESSION_COOKIE}={token}; Path=/; HttpOnly; SameSite=Lax; Max-Age={auth.SESSION_TTL_SECONDS}"
    )
    return Response.redirect("/dashboard", headers=[("Set-Cookie", cookie)])


@route("GET", "/logout")
def logout(request):
    """GET /logout — destroy the session and expire the cookie."""
    token = request.cookies.get(auth.SESSION_COOKIE)
    auth.destroy_session(token)
    cookie = f"{auth.SESSION_COOKIE}=; Path=/; HttpOnly; Max-Age=0"
    return Response.redirect("/login", headers=[("Set-Cookie", cookie)])


def template_login(request, error):
    """Render the standalone login page with an optional error banner."""
    from backend.routes import template
    from backend.routes.pref_routes import body_class

    shown = f'<p class="login-error">{template.esc(error)}</p>' if error else ""
    # The login page honors the theme cookie too (class on <html>, same
    # hook the app layout uses) — the preference applies everywhere.
    return template.render("login.html", error=shown, body_class=body_class(request))

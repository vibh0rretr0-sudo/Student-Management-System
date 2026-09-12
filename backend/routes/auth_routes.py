"""Login / logout routes."""
from backend import auth
from backend.models import professors
from backend.routes.helpers import Request, Response, route  # noqa: F401 (Request imported for type clarity)


@route("GET", "/login")
def login_form(request):
    if request.user:
        return Response.redirect("/dashboard")
    body = template_login(request, error="")
    return Response.html(body)


@route("POST", "/login")
def login_submit(request):
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
    token = request.cookies.get(auth.SESSION_COOKIE)
    auth.destroy_session(token)
    cookie = f"{auth.SESSION_COOKIE}=; Path=/; HttpOnly; Max-Age=0"
    return Response.redirect("/login", headers=[("Set-Cookie", cookie)])


def template_login(request, error):
    from backend.routes import template

    return template.render("login.html", error=error)

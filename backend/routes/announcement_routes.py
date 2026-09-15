"""Announcements tab: list, publish (with attachment), download, delete.

The publish route is the app's first multipart/form-data endpoint —
Request already split the file out of the POST body (helpers.py), so
this module is thin: validate via the model, redirect, done. Downloads
set Content-Disposition so the browser saves the file under its real
name instead of trying to render it.
"""
from urllib.parse import quote

from backend.models import announcements, courses
from backend.routes import template
from backend.routes.helpers import NotFound, Response, login_required, route
from backend.routes.validation import require


@route("GET", "/announcements")
@login_required
def list_page(request):
    """GET /announcements — audience-scoped list, newest first."""
    rows = announcements.list_for(request.user["id"])
    body = template.render(
        "announcements.html",
        rows=_rows_html(rows, request.user["id"]),
        # Empty-state message differs from 'no permission': the model
        # already filtered to what this professor may see.
        empty="" if rows else '<p class="empty">No announcements yet.</p>',
    )
    return Response.html(
        template.page(request, "Announcements", body, active="announcements")
    )


@route("GET", "/announcements/new")
@login_required
def new_form(request):
    """GET /announcements/new — publish form; audience = sections you teach."""
    my_sections = courses.sections_taught_by(request.user["id"])
    body = template.render(
        "announcement_form.html",
        form_title="Publish announcement",
        action="/announcements",
        section_options=_section_options(my_sections),
        title_value="",
        body_value="",
        cancel_link="/announcements",
        submit_label="Publish",
    )
    return Response.html(
        template.page(request, "New announcement", body, active="announcements")
    )


@route("POST", "/announcements")
@login_required
def publish(request):
    """POST /announcements — create; the optional file arrives via multipart."""
    require(request.form, "title", "body")
    section_id = request.form.get("section_id") or None
    if section_id is not None:
        section_id = int(section_id)  # model validates existence
    attachment = request.files.get("attachment")
    announcements.create(
        request.user["id"],
        request.form["title"].strip(),
        request.form["body"].strip(),
        section_id,
        attachment=attachment,
    )
    return Response.redirect("/announcements")


@route("GET", r"/announcements/(?P<announcement_id>\d+)/attachment")
@login_required
def download(request):
    """GET .../attachment — stream the stored bytes with the original filename."""
    announcement_id = int(request.params["announcement_id"])
    # Visibility check reuses the list rule: you may download only what
    # you could SEE (your sections or institute-wide). The subquery form
    # keeps the check in SQL — one round-trip, no TOCTOU gap.
    visible = db_visible(request.user["id"], announcement_id)
    if not visible:
        raise NotFound("That announcement does not exist or is not visible to you.")
    att = announcements.get_attachment(announcement_id)
    if att is None:
        raise NotFound("This announcement has no attachment.")
    # quote() makes the filename header-safe (spaces, unicode); ASCII
    # fallback for old clients, RFC 5987 form for modern ones.
    fname = att["filename"]
    headers = [
        (
            "Content-Disposition",
            f"attachment; filename=\"{fname.encode('ascii', 'replace').decode()}\"; filename*=UTF-8''{quote(fname)}",
        )
    ]
    return Response(200, att["file_bytes"], att["mime_type"], headers)


@route("POST", r"/announcements/(?P<announcement_id>\d+)/delete")
@login_required
def remove(request):
    """POST .../delete — author-only (the model raises PermissionError -> 403)."""
    announcements.delete(int(request.params["announcement_id"]), request.user["id"])
    return Response.redirect("/announcements")


def db_visible(professor_id, announcement_id):
    """Same audience rule as list_for, for a single row (download gate)."""
    from backend.models import db

    row = db.fetch_one(
        """
        SELECT a.id FROM announcements a
        WHERE a.id = %s
          AND (a.section_id IS NULL
               OR a.section_id IN (
                   SELECT c.section_id FROM courses c WHERE c.professor_id = %s
               ))
        """,
        (announcement_id, professor_id),
    )
    return row is not None


# ---------- helpers ----------

def _section_options(my_sections):
    """<option> list: institute-wide default + the professor's sections."""
    options = ['<option value="">All sections (institute-wide)</option>']
    for sec in my_sections:
        options.append(
            f'<option value="{sec["id"]}">{template.esc(sec["section_name"])}</option>'
        )
    return "".join(options)


def _rows_html(rows, viewer_id):
    """List rows: audience chip, attachment chip, author-only delete form."""
    if not rows:
        return '<tr><td colspan="4" class="empty">Nothing here yet.</td></tr>'
    parts = []
    for i, r in enumerate(rows):
        audience = (
            "Institute-wide" if r["is_institute_wide"] else f'Section {r["section_name"]}'
        )
        attachment = ""
        if r["attachment_name"]:
            size_kb = max(1, round((r["attachment_size"] or 0) / 1024))
            attachment = (
                f'<a class="attachment" href="/announcements/{r["id"]}/attachment">'
                f"📎 {template.esc(r['attachment_name'])} ({size_kb} KB)</a>"
            )
        # The delete button renders only for the author, but the MODEL
        # re-checks ownership on POST — hidden-in-UI is never the guard.
        delete_form = ""
        if r["professor_id"] == viewer_id:
            delete_form = (
                f'<form method="post" action="/announcements/{r["id"]}/delete" class="inline-form">'
                f'<button type="submit" class="btn btn-danger btn-sm">Delete</button></form>'
            )
        parts.append(
            f'<div class="card ann-card" style="--i:{i}">'
            f"<h2>{template.esc(r['title'])}</h2>"
            f'<p class="ann-meta">{template.esc(audience)} · {template.esc(r["author_name"])} · {r["published_at"]}</p>'
            f"<p>{template.esc(r['body'])}</p>"
            f"{attachment}"
            f"{delete_form}"
            f"</div>"
        )
    return "".join(parts)

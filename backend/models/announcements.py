"""Announcements: official notices with one optional attachment each.

Audience model (viva answer): an announcement targets a SECTION
(section_id set) or the whole institute (section_id NULL). The list
page scopes by the viewer's sections — a professor sees institute-wide
notices plus notices for the sections they teach, so the tab answers
"what concerns MY students".

Authorization follows the app-wide contract: ownership checks live in
THIS model (not the route), and violations raise PermissionError, which
dispatch() maps to 403. Any professor may PUBLISH; only the author may
DELETE — deleting something you didn't write is exactly the permission
line a real school would draw.
"""
from backend.models import db

# Upload policy lives with the storage decision it guards: 5 MB cap
# matches the server's protocol-level body limit, and the whitelist is
# documents/images only — no executables, no server-parsed types.
MAX_ATTACHMENT_BYTES = 5_000_000
ALLOWED_ATTACHMENT_TYPES = {
    "application/pdf": ".pdf",
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/gif": ".gif",
    "text/plain": ".txt",
}


def list_for(professor_id):
    """Announcements visible to this professor, newest first, with attachment info.

    WHERE logic: (announcement is institute-wide) OR (its section is one
    the professor teaches). The LEFT JOIN keeps announcements without
    attachments in the list (attachment columns come back NULL).
    """
    return db.fetch_all(
        """
        SELECT a.id, a.title, a.body, a.published_at, a.professor_id,
               p.name AS author_name,
               s.section_name,
               (a.section_id IS NULL) AS is_institute_wide,
               att.filename AS attachment_name,
               att.size_bytes AS attachment_size
        FROM announcements a
        JOIN professors p ON p.id = a.professor_id
        LEFT JOIN sections s ON s.id = a.section_id
        LEFT JOIN announcement_attachments att ON att.announcement_id = a.id
        WHERE a.section_id IS NULL
           OR a.section_id IN (
               SELECT c.section_id FROM courses c
               WHERE c.professor_id = %s
           )
        ORDER BY a.published_at DESC, a.id DESC
        """,
        (professor_id,),
    )


def get(announcement_id):
    """One announcement with author/section names, or None."""
    return db.fetch_one(
        """
        SELECT a.*, p.name AS author_name, s.section_name,
               (a.section_id IS NULL) AS is_institute_wide
        FROM announcements a
        JOIN professors p ON p.id = a.professor_id
        LEFT JOIN sections s ON s.id = a.section_id
        WHERE a.id = %s
        """,
        (announcement_id,),
    )


def create(professor_id, title, body, section_id, attachment=None):
    """Insert one announcement; attachment is a {filename, content_type, data} dict or None.

    Validation is model-level (raises ValueError -> 400) so the API is
    safe no matter which route calls it: unknown audience id, oversized
    file, or a MIME type outside the whitelist all fail here.
    """
    if section_id is not None:
        known = db.fetch_one("SELECT id FROM sections WHERE id = %s", (section_id,))
        if known is None:
            raise ValueError("That section does not exist.")
    if attachment is not None:
        _validate_attachment(attachment)

    announcement_id = db.execute(
        "INSERT INTO announcements (professor_id, section_id, title, body) VALUES (%s, %s, %s, %s)",
        (professor_id, section_id, title, body),
    )
    if attachment is not None:
        db.execute(
            """INSERT INTO announcement_attachments
               (announcement_id, filename, mime_type, file_bytes, size_bytes)
               VALUES (%s, %s, %s, %s, %s)""",
            (
                announcement_id,
                attachment["filename"],
                attachment["content_type"],
                attachment["data"],
                len(attachment["data"]),
            ),
        )
    return announcement_id


def delete(announcement_id, professor_id):
    """Delete an announcement — author only (else PermissionError -> 403).

    The attachment row goes with it via ON DELETE CASCADE: one DELETE,
    no orphan bytes.
    """
    row = db.fetch_one(
        "SELECT professor_id FROM announcements WHERE id = %s", (announcement_id,)
    )
    if row is None:
        from backend.routes.helpers import NotFound

        raise NotFound("That announcement does not exist.")
    if row["professor_id"] != professor_id:
        raise PermissionError("Only the author can delete this announcement.")
    db.execute("DELETE FROM announcements WHERE id = %s", (announcement_id,))


def get_attachment(announcement_id):
    """The attachment row for download (bytes + metadata), or None."""
    return db.fetch_one(
        """SELECT filename, mime_type, file_bytes, size_bytes
           FROM announcement_attachments WHERE announcement_id = %s""",
        (announcement_id,),
    )


def _validate_attachment(attachment):
    """Raise ValueError unless the upload fits the published policy."""
    data = attachment["data"]
    if not data:
        raise ValueError("The selected file is empty.")
    if len(data) > MAX_ATTACHMENT_BYTES:
        raise ValueError("Attachments are limited to 5 MB.")
    if attachment["content_type"] not in ALLOWED_ATTACHMENT_TYPES:
        raise ValueError(
            "Allowed attachment types: PDF, PNG, JPEG, GIF, or plain text."
        )
    # Defense in depth on the filename: keep the display name but strip
    # anything path-like, so 'objectionable/../../x.pdf' can never travel.
    safe_name = attachment["filename"].replace("\\", "/").split("/")[-1].strip()
    if not safe_name:
        raise ValueError("The file has no usable name.")
    attachment["filename"] = safe_name[:255]

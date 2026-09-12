"""Professor accounts and login verification."""
from backend.auth import verify_password
from backend.models import db


def get_by_id(professor_id):
    """Return a professor's public fields, or None."""
    return db.fetch_one(
        "SELECT id, username, name FROM professors WHERE id = %s", (professor_id,)
    )


def get_by_username(username):
    """Return the full professor row (including password_hash), or None."""
    return db.fetch_one("SELECT * FROM professors WHERE username = %s", (username,))


def verify_login(username, password):
    """Return the professor dict when credentials match, else None."""
    professor = get_by_username(username.strip())
    if professor and verify_password(password, professor["password_hash"]):
        return professor
    return None

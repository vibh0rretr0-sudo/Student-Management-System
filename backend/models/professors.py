"""Professor accounts and login verification.

Deliberately the smallest model — professors aren't CRUD-managed in the
UI; they're seeded accounts (scripts/setup_db.py). get_by_id() returns
only public fields (no password hash) because dispatch() attaches its
result to request.user, which templates render; get_by_username() is the
login path that DOES fetch the hash for verify_password().
"""
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
    # Same None for 'no such user' and 'wrong password': the response
    # never reveals which account names exist (no user enumeration).
    professor = get_by_username(username.strip())
    if professor and verify_password(password, professor["password_hash"]):
        return professor
    return None

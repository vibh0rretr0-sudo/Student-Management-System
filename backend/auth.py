"""Authentication: PBKDF2 password hashing + in-memory session store.

Passwords are salted PBKDF2-SHA256 (390,000 iterations) stored as
'pbkdf2_sha256$iterations$salt_hex$hash_hex'.

Sessions (confirmed decision) live in a Python dict, so every login is
lost when the server restarts. The session token is sent to the browser
as an HttpOnly cookie named sms_session.
"""
import hashlib
import hmac
import secrets
import threading
import time

ITERATIONS = 390000
SESSION_COOKIE = "sms_session"
SESSION_TTL_SECONDS = 7 * 24 * 60 * 60  # logins expire after a week

_sessions = {}
_lock = threading.Lock()


def hash_password(password: str) -> str:
    """Return 'pbkdf2_sha256$iterations$salt_hex$hash_hex' for storage."""
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, ITERATIONS)
    return f"pbkdf2_sha256${ITERATIONS}${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    """Check a password against a stored hash using constant-time compare."""
    try:
        algorithm, iterations, salt_hex, hash_hex = stored.split("$")
        if algorithm != "pbkdf2_sha256":
            return False
        digest = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), bytes.fromhex(salt_hex), int(iterations)
        )
        return hmac.compare_digest(digest.hex(), hash_hex)
    except (ValueError, AttributeError):
        return False


def create_session(professor_id: int) -> str:
    """Create a session for a professor and return its cookie token."""
    token = secrets.token_urlsafe(32)
    with _lock:
        _sessions[token] = {"professor_id": professor_id, "created_at": time.time()}
    return token


def get_session(token: str):
    """Return the session dict for a token, or None if missing or expired."""
    if not token:
        return None
    with _lock:
        session = _sessions.get(token)
        if session is None:
            return None
        if time.time() - session["created_at"] > SESSION_TTL_SECONDS:
            del _sessions[token]
            return None
        return session


def destroy_session(token: str) -> None:
    """Remove a session (logout)."""
    with _lock:
        _sessions.pop(token, None)

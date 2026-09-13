"""Authentication: PBKDF2 password hashing + in-memory session store.

Passwords are salted PBKDF2-SHA256 (390,000 iterations) stored as
'pbkdf2_sha256$iterations$salt_hex$hash_hex'.

WHY PBKDF2 (viva answer): hashing passwords with a deliberately slow
key-derivation function makes offline brute-force expensive; PBKDF2 is
the standard choice shipped in Python's stdlib — no third-party crypto.

WHY SESSIONS IN MEMORY (viva answer): a server restart logging everyone
out is acceptable for a single-process classroom app, and it removes an
entire class of store-the-token-safely problems. Scaling beyond one
process would mean swapping this dict for Redis/DB — the interface
(create/get/destroy) stays identical, which is the design lesson.

The session token is sent to the browser as an HttpOnly cookie named
sms_session; HttpOnly means JavaScript cannot read it, so a stolen
cookie can't be exfiltrated by an XSS payload.
"""
import hashlib
import hmac
import secrets
import threading
import time

# 390k rounds = ~0.1s per hash: fast enough for a login form, slow
# enough to make guessing a weak password impractical.
ITERATIONS = 390000
SESSION_COOKIE = "sms_session"
SESSION_TTL_SECONDS = 7 * 24 * 60 * 60  # logins expire after a week

# Server threads share these; ThreadingHTTPServer handles one thread per
# request, so every touch of the dict must take the lock.
_sessions = {}
_lock = threading.Lock()


def hash_password(password: str) -> str:
    """Return 'pbkdf2_sha256$iterations$salt_hex$hash_hex' for storage.

    A fresh random salt per password means two professors with the same
    password produce different stored hashes — rainbow tables are useless.
    """
    salt = secrets.token_bytes(16)  # 128 bits of randomness, never reused
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, ITERATIONS)
    return f"pbkdf2_sha256${ITERATIONS}${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    """Check a password against a stored hash using constant-time compare.

    hmac.compare_digest is the viva point: it takes the same time whether
    the bytes match early or late, so an attacker can't learn how many
    characters were right from response timing.
    """
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
    # 32 random bytes = impossible to guess a valid token by trying.
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

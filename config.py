"""Application configuration.

Values come from the environment (a lightweight .env loader keeps the
project dependency-free).  MySQL is the intended production engine; SQLite
is an equivalent local/dev fallback selected with DB_ENGINE=sqlite.
"""
import os
import secrets
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent


def load_env(path: Path | None = None) -> None:
    """Load KEY=VALUE pairs from .env without overriding real env vars."""
    path = path or BASE_DIR / ".env"
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key, value = key.strip(), value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


load_env()


def _bool(name: str, default: bool = False) -> bool:
    return os.environ.get(name, str(default)).strip().lower() in ("1", "true", "yes", "on")


def _int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default


class Config:
    ENV_NAME = os.environ.get("FLASK_ENV", os.environ.get("APP_ENV", "development"))
    DEBUG = _bool("FLASK_DEBUG", ENV_NAME != "production")

    # Flask needs a secret even though portal sessions live in the database.
    SECRET_KEY = os.environ.get("SECRET_KEY") or secrets.token_hex(32)

    # Relational database.  mysql (PyMySQL) or sqlite.
    DB_ENGINE = os.environ.get("DB_ENGINE", "sqlite").strip().lower()
    SQLITE_PATH = os.environ.get("SQLITE_PATH", str(BASE_DIR / "instance" / "jecrc.sqlite3"))
    MYSQL_HOST = os.environ.get("MYSQL_HOST", "127.0.0.1")
    MYSQL_PORT = _int("MYSQL_PORT", 3306)
    MYSQL_USER = os.environ.get("MYSQL_USER", "jecrc")
    MYSQL_PASSWORD = os.environ.get("MYSQL_PASSWORD", "")
    MYSQL_DATABASE = os.environ.get("MYSQL_DATABASE", "jecrc_portal")
    MYSQL_CHARSET = "utf8mb4"

    # Session policy
    SESSION_COOKIE_NAME = "jecrc_session"
    SESSION_IDLE_MINUTES = _int("SESSION_IDLE_MINUTES", 30)
    SESSION_WARN_MINUTES = _int("SESSION_WARN_MINUTES", 25)
    SESSION_HOURS = _int("SESSION_HOURS", 12)
    SESSION_REMEMBER_DAYS = _int("SESSION_REMEMBER_DAYS", 7)
    SESSION_COOKIE_SECURE = _bool("SESSION_COOKIE_SECURE", ENV_NAME == "production")

    # Uploads
    UPLOAD_DIR = os.environ.get("UPLOAD_DIR", str(BASE_DIR / "instance" / "uploads"))
    MAX_CONTENT_LENGTH = _int("MAX_UPLOAD_MB", 10) * 1024 * 1024
    ALLOWED_UPLOAD_EXTENSIONS = {"pdf", "png", "jpg", "jpeg", "docx", "zip"}
    ALLOWED_PHOTO_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}

    # Authentication hardening
    LOGIN_MAX_ATTEMPTS = _int("LOGIN_MAX_ATTEMPTS", 5)
    LOGIN_LOCK_MINUTES = _int("LOGIN_LOCK_MINUTES", 15)
    LOGIN_WINDOW_MINUTES = _int("LOGIN_WINDOW_MINUTES", 15)

    # Percentage used for the attendance warning.
    ATTENDANCE_THRESHOLD = _int("ATTENDANCE_THRESHOLD", 75)


class TestConfig(Config):
    ENV_NAME = "testing"
    TESTING = True
    DEBUG = False
    SECRET_KEY = "test-secret"
    DB_ENGINE = "sqlite"
    SQLITE_PATH = ":memory:"
    SESSION_COOKIE_SECURE = False
    LOGIN_MAX_ATTEMPTS = 5

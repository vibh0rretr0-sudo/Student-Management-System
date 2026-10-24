import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app import create_app  # noqa: E402
from app.db import db_from_config, init_db  # noqa: E402
from app.seed import seed  # noqa: E402


def make_config(db_path: Path, upload_dir: Path) -> dict:
    return {
        "TESTING": True,
        "DEBUG": False,
        "SECRET_KEY": "test-secret",
        "DB_ENGINE": "sqlite",
        "SQLITE_PATH": str(db_path),
        "UPLOAD_DIR": str(upload_dir),
        "SESSION_COOKIE_SECURE": False,
        "MAX_CONTENT_LENGTH": 2 * 1024 * 1024,
        "LOGIN_MAX_ATTEMPTS": 5,
        "LOGIN_LOCK_MINUTES": 15,
        "LOGIN_WINDOW_MINUTES": 15,
        "ATTENDANCE_THRESHOLD": 75,
        "SESSION_IDLE_MINUTES": 30,
        "SESSION_WARN_MINUTES": 25,
        "SESSION_HOURS": 12,
        "SESSION_REMEMBER_DAYS": 7,
    }


@pytest.fixture(scope="session")
def seeded_template(tmp_path_factory):
    """Build the demo dataset once; every test gets a private copy."""
    root = tmp_path_factory.mktemp("jecrc-template")
    db_path = root / "template.sqlite3"
    upload_dir = root / "uploads"
    app = create_app(make_config(db_path, upload_dir))
    with app.app_context():
        init_db(app)
        db = db_from_config(app.config)
        seed(db, upload_dir)
        db.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        db.close()
    return db_path, upload_dir


@pytest.fixture()
def app(seeded_template, tmp_path):
    template_db, template_uploads = seeded_template
    db_path = tmp_path / "test.sqlite3"
    shutil.copy(template_db, db_path)
    upload_dir = tmp_path / "uploads"
    shutil.copytree(template_uploads, upload_dir)
    return create_app(make_config(db_path, upload_dir))


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def db(app):
    database = db_from_config(app.config)
    try:
        yield database
    finally:
        database.close()

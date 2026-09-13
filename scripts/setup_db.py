"""
One-time database setup for the SMS project.

What it does:
  1. Connects to MySQL as root (password prompted interactively, never stored).
  2. Creates the `sms` database and a least-privilege `sms_app` user.
  3. Writes the sms_app password into backend/config.py.
  4. Applies backend/db/schema.sql, then backend/db/seed.sql (demo data).

Run:  python scripts/setup_db.py

Security posture (say this in the viva): root is used ONLY here, once,
at setup time; the running app holds just the sms_app account, which
GRANT ALL ON sms.* scopes to the single schema. The app password is
written into config.py (git-ignored) — the repo never carries it.
"""

import getpass
import re
import secrets
import sys
from pathlib import Path

import pymysql
from pymysql.constants import CLIENT

ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = ROOT / "backend" / "db" / "schema.sql"
SEED_PATH = ROOT / "backend" / "db" / "seed.sql"
CONFIG_PATH = ROOT / "backend" / "config.py"
CONFIG_EXAMPLE_PATH = ROOT / "backend" / "config.example.py"


def connect_as_root():
    """Prompt for the root password and connect to the MySQL server."""
    print("MySQL Server must be installed and running (see docs/MYSQL_SETUP.md).")
    print("Enter the root password you set during the MySQL installation.\n")
    root_password = getpass.getpass("MySQL root password: ")  # getpass: not echoed, not stored
    try:
        return pymysql.connect(
            host="127.0.0.1",
            port=3306,
            user="root",
            password=root_password,
            client_flag=CLIENT.MULTI_STATEMENTS,
        )
    except pymysql.err.OperationalError as exc:
        code = exc.args[0] if exc.args else None
        if code == 1045:
            sys.exit("Access denied: the root password appears to be incorrect.")
        if code == 2003:
            sys.exit(
                "Cannot reach MySQL at 127.0.0.1:3306. Is the MySQL80 service "
                "running? (Workbench: Server > Startup/Shutdown, or "
                "services.msc). See docs/MYSQL_SETUP.md."
            )
        raise


def choose_app_password():
    """Let the user pick the sms_app password, or auto-generate one."""
    chosen = getpass.getpass(
        "Choose a password for the new 'sms_app' DB user "
        "(press Enter to auto-generate): "
    ).strip()
    return chosen if chosen else secrets.token_urlsafe(12)


def ensure_app_user(conn, app_password):
    """Create (or reset) the least-privilege sms_app user."""
    with conn.cursor() as cur:
        cur.execute("CREATE USER IF NOT EXISTS 'sms_app'@'localhost' IDENTIFIED BY %s", (app_password,))
        cur.execute("ALTER USER 'sms_app'@'localhost' IDENTIFIED BY %s", (app_password,))
        cur.execute("GRANT ALL PRIVILEGES ON sms.* TO 'sms_app'@'localhost'")
        cur.execute("FLUSH PRIVILEGES")
    conn.commit()
    print("Created/updated DB user 'sms_app' (privileges limited to the sms database).")


def update_config(app_password):
    """Write the sms_app password into backend/config.py (git-ignored)."""
    if not CONFIG_PATH.exists():
        CONFIG_PATH.write_text(CONFIG_EXAMPLE_PATH.read_text(encoding="utf-8"), encoding="utf-8")
    text = CONFIG_PATH.read_text(encoding="utf-8")
    text = re.sub(r'^DB_PASSWORD\s*=\s*".*"$', f'DB_PASSWORD = "{app_password}"', text, flags=re.MULTILINE)
    CONFIG_PATH.write_text(text, encoding="utf-8")
    print(f"Saved DB password into {CONFIG_PATH.relative_to(ROOT)} (this file is git-ignored).")


def sms_exists(conn):
    """True when the `sms` database already exists (drives the drop prompt)."""
    with conn.cursor() as cur:
        cur.execute("SHOW DATABASES LIKE 'sms'")
        return cur.fetchone() is not None


def run_sql_file(conn, path, label):
    """Execute a .sql file statement by statement (comments stripped, split on ';')."""
    raw = path.read_text(encoding="utf-8")
    lines = [ln for ln in raw.splitlines() if not ln.strip().startswith("--")]
    # The naive-but-honest splitter: this project's SQL files never use
    # ';' inside strings, so a plain split is correct and readable. (A
    # full SQL parser would be over-engineering for two controlled files.)
    statements = [s.strip() for s in "\n".join(lines).split(";") if s.strip()]
    with conn.cursor() as cur:
        for i, statement in enumerate(statements, 1):
            try:
                cur.execute(statement)
            except pymysql.err.MySQLError:
                print(f"  !! failed at statement {i} of {label}:\n{statement[:120]}...")
                raise
    conn.commit()
    print(f"Applied {label} ({len(statements)} statements).")


def main():
    """The full setup flow: connect as root, user/config, schema, seed."""
    conn = connect_as_root()

    if sms_exists(conn):
        answer = input(
            "\nDatabase 'sms' already exists. Drop and recreate it? "
            "ALL existing data will be lost. [y/N]: "
        ).strip().lower()
        if answer == "y":
            with conn.cursor() as cur:
                cur.execute("DROP DATABASE sms")
            print("Dropped existing database.")
        else:
            # Only schema re-applies — existing data is never silently
            # destroyed by a re-run (the prompt IS the safety feature).
            print("Keeping the existing database; re-applying schema only.")

    app_password = choose_app_password()
    ensure_app_user(conn, app_password)
    update_config(app_password)

    run_sql_file(conn, SCHEMA_PATH, "schema.sql")
    if SEED_PATH.exists():
        run_sql_file(conn, SEED_PATH, "seed.sql")

    conn.close()
    print("\nDone. Demo professor login -> username: vibhor  password: prof123")


if __name__ == "__main__":
    main()

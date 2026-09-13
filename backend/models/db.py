"""MySQL connection factory + tiny query helpers.

Every model function opens a short-lived connection, runs parameterized
SQL, and closes it. All queries use %s placeholders so user input is
never concatenated into SQL strings (docs/OVERVIEW.md → Key Decisions).

WHY PARAMETERIZED (viva answer): with %s placeholders, the driver sends
the SQL and the values separately, so a name like `'); DROP TABLE--`
arrives as literal data, never as instructions. String-formatting SQL is
how SQL injection happens; this file is the only place connections are
made, so the guarantee holds everywhere.

WHY CONNECT-PER-QUERY (viva answer): naive, but correct for a classroom
app — no pool to tune, no leaked-connection bugs, and MySQL opens local
connections in ~1ms. A connection pool is the first upgrade if this ever
goes multi-user heavy; the four helpers below wouldn't change signature.
"""
import pymysql

from backend import config


def get_connection():
    """Open a new MySQL connection with dict-style rows.

    DictCursor means rows behave like dicts (row["name"]) — templates and
    handlers read fields by name, never by fragile column position.
    utf8mb4 = real Unicode (emoji in names survive).
    """
    return pymysql.connect(
        host=config.DB_HOST,
        port=config.DB_PORT,
        user=config.DB_USER,
        password=config.DB_PASSWORD,
        database=config.DB_NAME,
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
    )


def fetch_all(sql, params=()):
    """Run a SELECT and return every row as a list of dicts."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchall()
    finally:
        conn.close()


def fetch_one(sql, params=()):
    """Run a SELECT and return the first row as a dict (or None)."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchone()
    finally:
        conn.close()


def execute(sql, params=()):
    """Run one INSERT/UPDATE/DELETE, commit, and return lastrowid.

    One statement = one implicit transaction (MySQL autocommits a single
    statement atomically). The multi-row upserts in attendance.py are
    the exception — that's why mark_day() manages its own transaction.
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            conn.commit()
            return cur.lastrowid
    finally:
        conn.close()

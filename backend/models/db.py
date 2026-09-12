"""MySQL connection factory + tiny query helpers.

Every model function opens a short-lived connection, runs parameterized
SQL, and closes it. All queries use %s placeholders so user input is
never concatenated into SQL strings (Rules.md §2).
"""
import pymysql

from backend import config


def get_connection():
    """Open a new MySQL connection with dict-style rows."""
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
    """Run one INSERT/UPDATE/DELETE, commit, and return lastrowid."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            conn.commit()
            return cur.lastrowid
    finally:
        conn.close()

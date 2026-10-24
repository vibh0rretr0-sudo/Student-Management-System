"""Database access layer.

One connection per Flask request/context. SQL is written in a portable
subset with ``?`` placeholders; the MySQL adapter rewrites them to ``%s``.
Date/time values are handed to the driver as ISO strings so that MySQL and
SQLite behave identically.
"""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import date, datetime
from pathlib import Path

from flask import current_app, g


def _adapt(value):
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M:%S")
    if isinstance(value, date):
        return value.strftime("%Y-%m-%d")
    if isinstance(value, bool):
        return 1 if value else 0
    return value


def _adapt_all(params):
    return tuple(_adapt(p) for p in (params or ()))


class Database:
    """Thin, engine-agnostic wrapper around sqlite3 / PyMySQL."""

    def __init__(self, engine: str, **options):
        self.engine = engine
        self.options = options
        self._conn = None

    # -- connection -----------------------------------------------------
    def connect(self):
        if self.engine == "mysql":
            import pymysql
            from pymysql.cursors import DictCursor

            conn = pymysql.connect(
                host=self.options["host"],
                port=int(self.options["port"]),
                user=self.options["user"],
                password=self.options["password"],
                database=self.options["database"],
                charset="utf8mb4",
                cursorclass=DictCursor,
                autocommit=True,
            )
            return conn

        path = self.options["path"]
        if path != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(path, timeout=15, isolation_level=None,
                               check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")
        return conn

    @property
    def conn(self):
        if self._conn is None:
            self._conn = self.connect()
        return self._conn

    def close(self):
        if self._conn is not None:
            try:
                self._conn.close()
            finally:
                self._conn = None

    def _translate(self, sql: str) -> str:
        if self.engine == "mysql":
            return sql.replace("?", "%s")
        return sql

    # -- queries --------------------------------------------------------
    def query(self, sql: str, params=()):
        cur = self.conn.cursor()
        try:
            cur.execute(self._translate(sql), _adapt_all(params))
            rows = cur.fetchall()
            return [dict(r) for r in rows]
        finally:
            cur.close()

    def query_one(self, sql: str, params=()):
        rows = self.query(sql, params)
        return rows[0] if rows else None

    def scalar(self, sql: str, params=(), default=None):
        row = self.query_one(sql, params)
        if not row:
            return default
        value = next(iter(row.values()))
        return default if value is None else value

    def execute(self, sql: str, params=()):
        cur = self.conn.cursor()
        try:
            cur.execute(self._translate(sql), _adapt_all(params))
            return cur.lastrowid
        finally:
            cur.close()

    def execute_many(self, sql: str, seq_params):
        cur = self.conn.cursor()
        try:
            cur.executemany(self._translate(sql),
                            [_adapt_all(p) for p in seq_params])
            return cur.rowcount
        finally:
            cur.close()

    def insert(self, table: str, values: dict):
        cols = ", ".join(values.keys())
        marks = ", ".join("?" for _ in values)
        return self.execute(
            f"INSERT INTO {table} ({cols}) VALUES ({marks})",
            tuple(values.values()),
        )

    def update(self, table: str, values: dict, where: str, params=()):
        sets = ", ".join(f"{c} = ?" for c in values)
        return self.execute(
            f"UPDATE {table} SET {sets} WHERE {where}",
            tuple(values.values()) + tuple(params),
        )

    @contextmanager
    def transaction(self):
        """Group several statements atomically (works with autocommit on)."""
        conn = self.conn
        cur = conn.cursor()
        cur.execute("BEGIN")
        try:
            yield self
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            cur.close()

    # -- schema helpers -------------------------------------------------
    def table_names(self):
        if self.engine == "mysql":
            rows = self.query("SHOW TABLES")
            return {list(r.values())[0] for r in rows}
        rows = self.query("SELECT name FROM sqlite_master WHERE type='table'")
        return {r["name"] for r in rows}

    def is_empty(self):
        tables = self.table_names()
        if "users" not in tables:
            return True
        return (self.scalar("SELECT COUNT(*) AS c FROM users", default=0) or 0) == 0


def db_from_config(config) -> Database:
    if config["DB_ENGINE"] == "mysql":
        return Database(
            "mysql",
            host=config["MYSQL_HOST"],
            port=config["MYSQL_PORT"],
            user=config["MYSQL_USER"],
            password=config["MYSQL_PASSWORD"],
            database=config["MYSQL_DATABASE"],
        )
    return Database("sqlite", path=config["SQLITE_PATH"])


def get_db() -> Database:
    if "_db" not in g:
        g._db = db_from_config(current_app.config)
    return g._db


def close_db(_exc=None):
    db = g.pop("_db", None)
    if db is not None:
        db.close()


def init_db(app, drop: bool = False):
    """Create the schema from the matching SQL file."""
    engine = app.config["DB_ENGINE"]
    filename = "schema_sqlite.sql" if engine == "sqlite" else "schema.sql"
    schema_path = Path(app.root_path).parent / "database" / filename
    sql = schema_path.read_text(encoding="utf-8")

    db = db_from_config(app.config)
    try:
        existing = db.table_names()
        if not drop and "users" in existing:
            return
        if drop:
            tables = sorted(existing - {"sqlite_sequence"})
            if db.engine == "mysql":
                db.execute("SET FOREIGN_KEY_CHECKS = 0")
            else:
                # SQLite enforces FKs on DROP unless we turn the pragma off;
                # alphabetical order can otherwise hit a "constraint failed".
                db.execute("PRAGMA foreign_keys = OFF")
            for table in tables:
                db.execute(f"DROP TABLE IF EXISTS {table}")
            if db.engine == "mysql":
                db.execute("SET FOREIGN_KEY_CHECKS = 1")
            else:
                db.execute("PRAGMA foreign_keys = ON")

        statements = []
        buffer = ""
        for line in sql.splitlines():
            stripped = line.strip()
            if not buffer and (not stripped or stripped.startswith("--")):
                continue
            buffer += line + "\n"
            if stripped.endswith(";"):
                statements.append(buffer.strip())
                buffer = ""
        if buffer.strip():
            statements.append(buffer.strip())

        for statement in statements:
            db.execute(statement)
    finally:
        db.close()


def reset_memory_db(db: Database, app):
    """(:memory:) databases are per-connection; tests use a shared file."""
    return db

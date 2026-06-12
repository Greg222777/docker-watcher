import sqlite3
from collections.abc import Iterable
from contextlib import closing
from pathlib import Path

from app.config import DB_PATH

SCHEMA_MIGRATIONS_TABLE = "schema_migrations"
APPLICATION_TABLES = {"container_events", "monitored_event_actions"}

MIGRATIONS = [
    (
        "0001_initial_schema",
        """
        CREATE TABLE container_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            container_name TEXT NOT NULL,
            container_id TEXT NOT NULL,
            action TEXT NOT NULL,
            exit_code TEXT,
            log_file_path TEXT,
            created_at TEXT NOT NULL
        );

        CREATE TABLE monitored_event_actions (
            action TEXT PRIMARY KEY
        );
        """,
    )
]


def run_migrations(db_path: str | Path = DB_PATH) -> None:
    with closing(sqlite3.connect(db_path)) as conn:
        with conn:
            _create_schema_migrations_table(conn)

            if _has_existing_unversioned_schema(conn):
                _mark_migrations_as_applied(
                    conn,
                    (revision for revision, _sql in MIGRATIONS),
                )
                return

            applied_revisions = _select_applied_revisions(conn)

            for revision, sql in MIGRATIONS:
                if revision not in applied_revisions:
                    conn.executescript(sql)
                    _mark_migrations_as_applied(conn, [revision])


def _create_schema_migrations_table(conn: sqlite3.Connection) -> None:
    conn.execute(f"""
        CREATE TABLE IF NOT EXISTS {SCHEMA_MIGRATIONS_TABLE} (
            revision TEXT PRIMARY KEY,
            applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """)


def _has_existing_unversioned_schema(conn: sqlite3.Connection) -> bool:
    table_names = _select_table_names(conn)

    if not APPLICATION_TABLES.issubset(table_names):
        return False

    applied_revisions = _select_applied_revisions(conn)
    return len(applied_revisions) == 0


def _select_table_names(conn: sqlite3.Connection) -> set[str]:
    rows = conn.execute("""
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
    """).fetchall()

    return {row[0] for row in rows}


def _select_applied_revisions(conn: sqlite3.Connection) -> set[str]:
    rows = conn.execute(f"""
        SELECT revision
        FROM {SCHEMA_MIGRATIONS_TABLE}
    """).fetchall()

    return {row[0] for row in rows}


def _mark_migrations_as_applied(
    conn: sqlite3.Connection,
    revisions: Iterable[str],
) -> None:
    conn.executemany(
        f"""
        INSERT OR IGNORE INTO {SCHEMA_MIGRATIONS_TABLE} (revision)
        VALUES (?)
        """,
        [(revision,) for revision in revisions],
    )

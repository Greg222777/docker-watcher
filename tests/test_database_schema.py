import sqlite3
from pathlib import Path
from uuid import uuid4

import pytest

from app.database.schema import run_migrations

TEST_DIR = Path(__file__).resolve().parent


@pytest.fixture
def db_path() -> Path:
    path = TEST_DIR / f"schema_{uuid4().hex}.db"

    yield path

    try:
        if path.exists():
            path.unlink()
    except PermissionError:
        pass


def test_run_migrations_creates_schema(db_path) -> None:
    run_migrations(db_path)

    with sqlite3.connect(db_path) as conn:
        table_names = _select_table_names(conn)
        revisions = _select_revisions(conn)

    assert "schema_migrations" in table_names
    assert "container_events" in table_names
    assert "monitored_event_actions" in table_names
    assert revisions == {"0001_initial_schema"}


def test_run_migrations_marks_existing_schema_as_applied(db_path) -> None:
    with sqlite3.connect(db_path) as conn:
        conn.executescript("""
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
        """)

    run_migrations(db_path)

    with sqlite3.connect(db_path) as conn:
        revisions = _select_revisions(conn)

    assert revisions == {"0001_initial_schema"}


def _select_table_names(conn: sqlite3.Connection) -> set[str]:
    rows = conn.execute("""
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
    """).fetchall()

    return {row[0] for row in rows}


def _select_revisions(conn: sqlite3.Connection) -> set[str]:
    rows = conn.execute("""
        SELECT revision
        FROM schema_migrations
    """).fetchall()

    return {row[0] for row in rows}

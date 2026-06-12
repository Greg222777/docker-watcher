import sqlite3
from pathlib import Path
from uuid import uuid4

import pytest

from app.database.migrations import run_migrations

TEST_DIR = Path(__file__).resolve().parent


@pytest.fixture
def db_path() -> Path:
    path = TEST_DIR / f"migrations_{uuid4().hex}.db"

    yield path

    try:
        if path.exists():
            path.unlink()
    except PermissionError:
        pass


def test_run_migrations_creates_schema(db_path) -> None:
    run_migrations(db_path)

    with sqlite3.connect(db_path) as conn:
        table_names = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }

    assert "alembic_version" in table_names
    assert "container_events" in table_names
    assert "monitored_event_actions" in table_names


def test_run_migrations_stamps_existing_schema(db_path) -> None:
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
        version = conn.execute("SELECT version_num FROM alembic_version").fetchone()[0]

    assert version == "0001"

import sqlite3
from datetime import datetime
from typing import Optional, Any

DB_PATH = "/data/docker_events.db"


def init_db() -> None:
    """
    Initialize the database and create the events table if it does not exist.
    """
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS container_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                container_name TEXT NOT NULL,
                container_id TEXT NOT NULL,
                action TEXT NOT NULL,
                exit_code TEXT,
                log_file_path TEXT,
                created_at TEXT NOT NULL
            )
        """)


def save_event(
    container_name: str,
    container_id: str,
    action: str,
    exit_code: Optional[str] = None,
    log_file_path: Optional[str] = None
) -> None:
    """
    Save a Docker container event in the database.
    """
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            INSERT INTO container_events (
                container_name,
                container_id,
                action,
                exit_code,
                log_file_path,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            container_name,
            container_id,
            action,
            exit_code,
            log_file_path,
            datetime.now().isoformat()
        ))


def delete_event(event_id: int) -> None:
    """
    Delete a single event by its database ID.
    """
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            DELETE FROM container_events
            WHERE id = ?
        """, (event_id,))


def delete_all_events() -> None:
    """
    Delete all events from the database.
    """
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("DELETE FROM container_events")


def select_events_between(
    start_timestamp: int,
    end_timestamp: int
) -> list[dict[str, Any]]:
    """
    Retrieve events between two timestamps.
    """
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row

        cursor = conn.execute("""
            SELECT *
            FROM container_events
            WHERE created_at BETWEEN ? AND ?
            ORDER BY created_at DESC
        """, (
            start_timestamp,
            end_timestamp
        ))

        return [dict(row) for row in cursor.fetchall()]


def select_all_events() -> list[dict[str, Any]]:
    """
    Retrieve all events ordered by creation date descending.
    """
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row

        cursor = conn.execute("""
            SELECT *
            FROM container_events
            ORDER BY created_at DESC
        """)

        return [dict(row) for row in cursor.fetchall()]
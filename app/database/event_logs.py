import sqlite3

from app.models import EventLog


DB_PATH = "/data/docker_events.db"


class EventLogRepository:
    def __init__(self, db_path: str = DB_PATH) -> None:
        self.db_path = db_path

    def init_db(self) -> None:
        """
        Initialize the database and create the events table if it does not exist.
        """
        with sqlite3.connect(self.db_path) as conn:
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

    def save(self, event: EventLog) -> None:
        """
        Save a Docker container event in the database.
        """
        with sqlite3.connect(self.db_path) as conn:
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
            """, event.to_insert_values())

    def delete(self, event_id: int) -> None:
        """
        Delete a single event by its database ID.
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                DELETE FROM container_events
                WHERE id = ?
            """, (event_id,))

    def delete_all(self) -> None:
        """
        Delete all events from the database.
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM container_events")

    def select_between(
        self,
        start_timestamp: str,
        end_timestamp: str
    ) -> list[EventLog]:
        """
        Retrieve events between two ISO timestamps.
        """
        with sqlite3.connect(self.db_path) as conn:
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

            return [EventLog.from_row(dict(row)) for row in cursor.fetchall()]

    def select_all(self) -> list[EventLog]:
        """
        Retrieve all events ordered by creation date descending.
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            cursor = conn.execute("""
                SELECT *
                FROM container_events
                ORDER BY created_at DESC
            """)

            return [EventLog.from_row(dict(row)) for row in cursor.fetchall()]

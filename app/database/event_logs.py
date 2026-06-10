import sqlite3
from contextlib import closing

from app.config import DB_PATH
from app.models import EventLog


class EventLogRepository:
    def __init__(self, db_path: str | None = None) -> None:
        self.db_path = str(db_path or DB_PATH)

    def init_db(self) -> None:
        """
        Initialize the database and create the events table if it does not exist.
        """
        with closing(sqlite3.connect(self.db_path)) as conn:
            with conn:
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
        with closing(sqlite3.connect(self.db_path)) as conn:
            with conn:
                conn.execute(
                    """
                    INSERT INTO container_events (
                        container_name,
                        container_id,
                        action,
                        exit_code,
                        log_file_path,
                        created_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?)
                """,
                    event.to_insert_values(),
                )

    def delete(self, event_id: int) -> None:
        """
        Delete a single event by its database ID.
        """
        with closing(sqlite3.connect(self.db_path)) as conn:
            with conn:
                conn.execute(
                    """
                    DELETE FROM container_events
                    WHERE id = ?
                """,
                    (event_id,),
                )

    def delete_all(self) -> None:
        """
        Delete all events from the database.
        """
        with closing(sqlite3.connect(self.db_path)) as conn:
            with conn:
                conn.execute("DELETE FROM container_events")

    def select_by_id(self, event_id: int) -> EventLog | None:
        """
        Retrieve one event by its database ID.
        """
        with closing(sqlite3.connect(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row

            cursor = conn.execute(
                """
                SELECT *
                FROM container_events
                WHERE id = ?
            """,
                (event_id,),
            )
            row = cursor.fetchone()

            return EventLog.from_row(dict(row)) if row else None

    def select_between(
        self, start_timestamp: str, end_timestamp: str
    ) -> list[EventLog]:
        """
        Retrieve events between two ISO timestamps.
        """
        with closing(sqlite3.connect(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row

            cursor = conn.execute(
                """
                SELECT *
                FROM container_events
                WHERE created_at BETWEEN ? AND ?
                ORDER BY created_at DESC
            """,
                (start_timestamp, end_timestamp),
            )

            return [EventLog.from_row(dict(row)) for row in cursor.fetchall()]

    def select_filtered(
        self,
        start_timestamp: str,
        end_timestamp: str,
        container_filter: str,
        action_filter: str,
        limit: int,
        offset: int,
    ) -> list[EventLog]:
        """
        Retrieve a filtered page of events ordered by creation date descending.
        """
        where_clause, params = self._build_filter_clause(
            start_timestamp=start_timestamp,
            end_timestamp=end_timestamp,
            container_filter=container_filter,
            action_filter=action_filter,
        )

        with closing(sqlite3.connect(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row

            cursor = conn.execute(
                f"""
                SELECT *
                FROM container_events
                {where_clause}
                ORDER BY created_at DESC
                LIMIT ?
                OFFSET ?
            """,
                [*params, limit, offset],
            )

            return [EventLog.from_row(dict(row)) for row in cursor.fetchall()]

    def count_filtered(
        self,
        start_timestamp: str,
        end_timestamp: str,
        container_filter: str,
        action_filter: str,
    ) -> int:
        """
        Count events matching the same filters used for paginated retrieval.
        """
        where_clause, params = self._build_filter_clause(
            start_timestamp=start_timestamp,
            end_timestamp=end_timestamp,
            container_filter=container_filter,
            action_filter=action_filter,
        )

        with closing(sqlite3.connect(self.db_path)) as conn:
            cursor = conn.execute(
                f"""
                SELECT COUNT(*)
                FROM container_events
                {where_clause}
            """,
                params,
            )

            return int(cursor.fetchone()[0])

    def select_all(self) -> list[EventLog]:
        """
        Retrieve all events ordered by creation date descending.
        """
        with closing(sqlite3.connect(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row

            cursor = conn.execute("""
                SELECT *
                FROM container_events
                ORDER BY created_at DESC
            """)

            return [EventLog.from_row(dict(row)) for row in cursor.fetchall()]

    def _build_filter_clause(
        self,
        start_timestamp: str,
        end_timestamp: str,
        container_filter: str,
        action_filter: str,
    ) -> tuple[str, list[str]]:
        clauses = []
        params = []

        if start_timestamp:
            clauses.append("created_at >= ?")
            params.append(start_timestamp)

        if end_timestamp:
            clauses.append("created_at <= ?")
            params.append(end_timestamp)

        if container_filter:
            clauses.append("""
                (
                    LOWER(container_name) LIKE ?
                    OR LOWER(container_id) LIKE ?
                )
            """)
            normalized_filter = f"%{container_filter.lower()}%"
            params.extend([normalized_filter, normalized_filter])

        if action_filter:
            clauses.append("(action = ? OR action LIKE ?)")
            params.extend([action_filter, f"{action_filter}:%"])

        if not clauses:
            return "", params

        return f"WHERE {' AND '.join(clauses)}", params

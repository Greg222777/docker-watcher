import sqlite3
from contextlib import closing

from app.config import DB_PATH
from app.models import DEFAULT_MONITORED_EVENT_ACTIONS, DockerEventAction


class MonitoredEventActionRepository:
    def __init__(self, db_path: str | None = None) -> None:
        self.db_path = str(db_path or DB_PATH)

    def init_db(self) -> None:
        """
        Initialize monitored Docker event actions.

        The default selection focuses on abnormal or operationally important
        container states. Existing user choices are preserved across restarts.
        """
        with closing(sqlite3.connect(self.db_path)) as conn:
            with conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS monitored_event_actions (
                        action TEXT PRIMARY KEY
                    )
                """)

                existing_count = conn.execute("""
                    SELECT COUNT(*)
                    FROM monitored_event_actions
                """).fetchone()[0]

                if existing_count == 0:
                    conn.executemany(
                        """
                        INSERT INTO monitored_event_actions (action)
                        VALUES (?)
                    """,
                        [
                            (action.value,)
                            for action in sorted(
                                DEFAULT_MONITORED_EVENT_ACTIONS,
                                key=lambda item: item.value,
                            )
                        ],
                    )

    def select_all(self) -> set[DockerEventAction]:
        with closing(sqlite3.connect(self.db_path)) as conn:
            cursor = conn.execute("""
                SELECT action
                FROM monitored_event_actions
                ORDER BY action
            """)

            return {
                action
                for row in cursor.fetchall()
                if (action := DockerEventAction.from_raw(row[0])) is not None
            }

    def replace_all(self, actions: set[DockerEventAction]) -> None:
        with closing(sqlite3.connect(self.db_path)) as conn:
            with conn:
                conn.execute("DELETE FROM monitored_event_actions")
                conn.executemany(
                    """
                    INSERT INTO monitored_event_actions (action)
                    VALUES (?)
                """,
                    [
                        (action.value,)
                        for action in sorted(actions, key=lambda item: item.value)
                    ],
                )

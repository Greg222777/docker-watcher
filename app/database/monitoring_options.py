from sqlalchemy import func, select

from app.config import DB_PATH
from app.database.schema import run_migrations
from app.database.session import create_session_factory
from app.database.tables import MonitoredEventActionRecord
from app.models import DEFAULT_MONITORED_EVENT_ACTIONS, DockerEventAction


class MonitoredEventActionRepository:
    def __init__(self, db_path: str | None = None) -> None:
        self.db_path = str(db_path or DB_PATH)
        self.session_factory = create_session_factory(self.db_path)

    def init_db(self) -> None:
        """
        Apply database migrations and initialize monitored Docker event actions.

        The default selection focuses on abnormal or operationally important
        container states. Existing user choices are preserved across restarts.
        """
        run_migrations(self.db_path)
        self.seed_defaults()

    def seed_defaults(self) -> None:
        with self.session_factory.begin() as session:
            existing_count = session.scalar(
                select(func.count()).select_from(MonitoredEventActionRecord)
            )

            if existing_count == 0:
                session.add_all(
                    [
                        MonitoredEventActionRecord(action=action.value)
                        for action in sorted(
                            DEFAULT_MONITORED_EVENT_ACTIONS,
                            key=lambda item: item.value,
                        )
                    ]
                )

    def select_all(self) -> set[DockerEventAction]:
        with self.session_factory() as session:
            actions = session.scalars(
                select(MonitoredEventActionRecord.action).order_by(
                    MonitoredEventActionRecord.action
                )
            )

            return {
                action
                for raw_action in actions
                if (action := DockerEventAction.from_raw(raw_action)) is not None
            }

    def replace_all(self, actions: set[DockerEventAction]) -> None:
        with self.session_factory.begin() as session:
            session.query(MonitoredEventActionRecord).delete()
            session.add_all(
                [
                    MonitoredEventActionRecord(action=action.value)
                    for action in sorted(actions, key=lambda item: item.value)
                ]
            )

from sqlalchemy import func, or_, select
from sqlalchemy.sql.elements import ColumnElement

from app.config import DB_PATH
from app.database.schema import run_migrations
from app.database.session import create_session_factory
from app.database.tables import ContainerEventRecord
from app.models import EventLog


class EventLogRepository:
    def __init__(self, db_path: str | None = None) -> None:
        self.db_path = str(db_path or DB_PATH)
        self.session_factory = create_session_factory(self.db_path)

    def init_db(self) -> None:
        """
        Apply database migrations.
        """
        run_migrations(self.db_path)

    def save(self, event: EventLog) -> None:
        """
        Save a Docker container event in the database.
        """
        with self.session_factory.begin() as session:
            session.add(ContainerEventRecord.from_event_log(event))

    def delete(self, event_id: int) -> None:
        """
        Delete a single event by its database ID.
        """
        with self.session_factory.begin() as session:
            event = session.get(ContainerEventRecord, event_id)
            if event is not None:
                session.delete(event)

    def delete_all(self) -> None:
        """
        Delete all events from the database.
        """
        with self.session_factory.begin() as session:
            session.query(ContainerEventRecord).delete()

    def select_by_id(self, event_id: int) -> EventLog | None:
        """
        Retrieve one event by its database ID.
        """
        with self.session_factory() as session:
            record = session.get(ContainerEventRecord, event_id)

            return record.to_event_log() if record else None

    def select_between(
        self, start_timestamp: str, end_timestamp: str
    ) -> list[EventLog]:
        """
        Retrieve events between two ISO timestamps.
        """
        with self.session_factory() as session:
            records = session.scalars(
                select(ContainerEventRecord)
                .where(
                    ContainerEventRecord.created_at.between(
                        start_timestamp, end_timestamp
                    )
                )
                .order_by(ContainerEventRecord.created_at.desc())
            )

            return [record.to_event_log() for record in records]

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
        filters = self._build_filters(
            start_timestamp=start_timestamp,
            end_timestamp=end_timestamp,
            container_filter=container_filter,
            action_filter=action_filter,
        )

        with self.session_factory() as session:
            records = session.scalars(
                select(ContainerEventRecord)
                .where(*filters)
                .order_by(ContainerEventRecord.created_at.desc())
                .limit(limit)
                .offset(offset)
            )

            return [record.to_event_log() for record in records]

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
        filters = self._build_filters(
            start_timestamp=start_timestamp,
            end_timestamp=end_timestamp,
            container_filter=container_filter,
            action_filter=action_filter,
        )

        with self.session_factory() as session:
            count = session.scalar(
                select(func.count()).select_from(ContainerEventRecord).where(*filters)
            )

            return int(count or 0)

    def select_all(self) -> list[EventLog]:
        """
        Retrieve all events ordered by creation date descending.
        """
        with self.session_factory() as session:
            records = session.scalars(
                select(ContainerEventRecord).order_by(
                    ContainerEventRecord.created_at.desc()
                )
            )

            return [record.to_event_log() for record in records]

    def _build_filters(
        self,
        start_timestamp: str,
        end_timestamp: str,
        container_filter: str,
        action_filter: str,
    ) -> list[ColumnElement[bool]]:
        filters = []

        if start_timestamp:
            filters.append(ContainerEventRecord.created_at >= start_timestamp)

        if end_timestamp:
            filters.append(ContainerEventRecord.created_at <= end_timestamp)

        if container_filter:
            normalized_filter = f"%{container_filter.lower()}%"
            filters.append(
                or_(
                    func.lower(ContainerEventRecord.container_name).like(
                        normalized_filter
                    ),
                    func.lower(ContainerEventRecord.container_id).like(
                        normalized_filter
                    ),
                )
            )

        if action_filter:
            filters.append(
                or_(
                    ContainerEventRecord.action == action_filter,
                    ContainerEventRecord.action.like(f"{action_filter}:%"),
                )
            )

        return filters

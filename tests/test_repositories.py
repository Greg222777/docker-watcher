from pathlib import Path
from uuid import uuid4

import pytest

from app.database.event_logs import EventLogRepository
from app.database.monitoring_options import MonitoredEventActionRepository
from app.database.schema import init_schema
from app.models.docker_event_action import (
    DEFAULT_MONITORED_EVENT_ACTIONS,
    DockerEventAction,
)
from app.models.event_log import EventLog


@pytest.fixture
def db_path() -> Path:
    path = Path(__file__).resolve().parent / f"repository_{uuid4().hex}.db"

    yield path

    path.unlink(missing_ok=True)


@pytest.fixture
def event_log_repository(db_path: Path) -> EventLogRepository:
    init_schema(db_path)

    return EventLogRepository(str(db_path))


@pytest.fixture
def monitored_action_repository(db_path: Path) -> MonitoredEventActionRepository:
    init_schema(db_path)

    return MonitoredEventActionRepository(str(db_path))


class TestEventLogRepository:
    def test_saves_and_retrieves_event_by_id(
        self,
        event_log_repository: EventLogRepository,
    ) -> None:
        event = EventLog(
            container_name="api",
            container_id="container-123",
            action="die",
            exit_code="137",
            log_file_path="logs/api.log",
            created_at="2026-06-18T10:00:00",
        )

        event_log_repository.save(event)

        saved_events = event_log_repository.select_filtered("", "", "", "", 10, 0)
        saved_event = saved_events[0]

        assert saved_event.id is not None
        assert event_log_repository.select_by_id(saved_event.id) == saved_event

    def test_filters_and_counts_events(
        self,
        event_log_repository: EventLogRepository,
    ) -> None:
        event_log_repository.save(
            EventLog(
                container_name="api",
                container_id="abc123",
                action="die",
                created_at="2026-06-18T10:00:00",
            )
        )
        event_log_repository.save(
            EventLog(
                container_name="worker",
                container_id="def456",
                action="health_status: unhealthy",
                created_at="2026-06-18T11:00:00",
            )
        )

        filtered_events = event_log_repository.select_filtered(
            start_timestamp="2026-06-18T10:30:00",
            end_timestamp="",
            container_filter="WORK",
            action_filter="health_status",
            limit=10,
            offset=0,
        )

        assert len(filtered_events) == 1
        assert filtered_events[0].container_name == "worker"
        assert event_log_repository.count_filtered("", "", "", "") == 2

    def test_deletes_all_events(
        self,
        event_log_repository: EventLogRepository,
    ) -> None:
        event_log_repository.save(
            EventLog(container_name="api", container_id="abc123", action="die")
        )

        event_log_repository.delete_all()

        assert event_log_repository.count_filtered("", "", "", "") == 0


class TestMonitoredEventActionRepository:
    def test_seeds_defaults_only_when_table_is_empty(
        self,
        monitored_action_repository: MonitoredEventActionRepository,
    ) -> None:
        monitored_action_repository.seed_defaults()

        assert (
            monitored_action_repository.select_all() == DEFAULT_MONITORED_EVENT_ACTIONS
        )

        monitored_action_repository.replace_all({DockerEventAction.DIE})
        monitored_action_repository.seed_defaults()

        assert monitored_action_repository.select_all() == {DockerEventAction.DIE}

    def test_replaces_monitored_actions(
        self,
        monitored_action_repository: MonitoredEventActionRepository,
    ) -> None:
        monitored_action_repository.replace_all(
            {DockerEventAction.DIE, DockerEventAction.OOM}
        )

        assert monitored_action_repository.select_all() == {
            DockerEventAction.DIE,
            DockerEventAction.OOM,
        }

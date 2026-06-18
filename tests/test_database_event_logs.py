from app.database.event_logs import EventLogRepository
from app.database.schema import init_schema
from app.models.event_log import EventLog


def test_event_log_repository_saves_and_retrieves_events(tmp_path) -> None:
    db_path = tmp_path / "docker_events.db"
    repository = EventLogRepository(str(db_path))
    init_schema(db_path)
    event = EventLog(
        container_name="api",
        container_id="abcdef1234567890",
        action="die",
        exit_code="1",
        log_file_path="/data/logs/api.log",
        created_at="2026-06-02T10:00:00",
    )

    repository.save(event)
    events = repository.select_filtered(
        start_timestamp="",
        end_timestamp="",
        container_filter="",
        action_filter="",
        limit=10,
        offset=0,
    )

    assert len(events) == 1
    saved_event = events[0]
    assert saved_event.id is not None
    assert saved_event.container_name == "api"
    assert saved_event.container_id == "abcdef1234567890"
    assert saved_event.action == "die"
    assert saved_event.exit_code == "1"
    assert saved_event.log_file_path == "/data/logs/api.log"
    assert saved_event.created_at == "2026-06-02T10:00:00"


def test_event_log_repository_filters_and_counts_events(tmp_path) -> None:
    db_path = tmp_path / "docker_events.db"
    repository = EventLogRepository(str(db_path))
    init_schema(db_path)
    repository.save(
        EventLog(
            container_name="api",
            container_id="abcdef1234567890",
            action="health_status: unhealthy",
            created_at="2026-06-02T10:00:00",
        )
    )
    repository.save(
        EventLog(
            container_name="worker",
            container_id="123456abcdef7890",
            action="die",
            created_at="2026-06-03T10:00:00",
        )
    )

    events = repository.select_filtered(
        start_timestamp="2026-06-01T00:00:00",
        end_timestamp="2026-06-03T00:00:00",
        container_filter="API",
        action_filter="health_status",
        limit=10,
        offset=0,
    )

    assert [event.container_name for event in events] == ["api"]
    assert (
        repository.count_filtered(
            start_timestamp="2026-06-01T00:00:00",
            end_timestamp="2026-06-03T00:00:00",
            container_filter="api",
            action_filter="health_status",
        )
        == 1
    )

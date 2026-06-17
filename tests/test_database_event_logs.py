from pathlib import Path
from uuid import uuid4

import pytest

from app.database import EventLogRepository
from app.database.schema import init_schema
from app.models import EventLog

TEST_DIR = Path(__file__).resolve().parent


@pytest.fixture
def db_path() -> Path:
    path = TEST_DIR / f"event_logs_{uuid4().hex}.db"

    yield path

    try:
        if path.exists():
            path.unlink()
    except PermissionError:
        pass


def test_event_log_repository_saves_and_retrieves_events(db_path) -> None:
    repository = EventLogRepository(str(db_path))
    init_schema(db_path)
    repository.save(
        EventLog(
            container_name="api",
            container_id="abcdef1234567890",
            action="die",
            exit_code="1",
            log_file_path="/data/logs/api.log",
            created_at="2026-06-02T10:00:00",
        )
    )

    events = repository.select_all()

    assert len(events) == 1
    assert events[0].id is not None
    assert events[0].container_name == "api"
    assert events[0].container_id == "abcdef1234567890"
    assert events[0].action == "die"
    assert events[0].exit_code == "1"
    assert events[0].log_file_path == "/data/logs/api.log"
    assert events[0].created_at == "2026-06-02T10:00:00"


def test_event_log_repository_filters_and_counts_events(db_path) -> None:
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

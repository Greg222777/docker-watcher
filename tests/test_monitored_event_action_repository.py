from pathlib import Path
from uuid import uuid4

import pytest

from app.database.monitoring_options import MonitoredEventActionRepository
from app.database.schema import init_schema
from app.models.docker_event_action import (
    DEFAULT_MONITORED_EVENT_ACTIONS,
    DockerEventAction,
)


@pytest.fixture
def monitored_action_repository() -> MonitoredEventActionRepository:
    db_path = Path(__file__).resolve().parent / f"monitored_actions_{uuid4().hex}.db"
    init_schema(db_path)

    yield MonitoredEventActionRepository(str(db_path))

    db_path.unlink(missing_ok=True)


def test_seeds_defaults_only_when_table_is_empty(
    monitored_action_repository: MonitoredEventActionRepository,
) -> None:
    monitored_action_repository.seed_defaults()

    assert monitored_action_repository.select_all() == DEFAULT_MONITORED_EVENT_ACTIONS

    monitored_action_repository.replace_all({DockerEventAction.DIE})
    monitored_action_repository.seed_defaults()

    assert monitored_action_repository.select_all() == {DockerEventAction.DIE}


def test_replaces_monitored_actions(
    monitored_action_repository: MonitoredEventActionRepository,
) -> None:
    monitored_action_repository.replace_all(
        {DockerEventAction.DIE, DockerEventAction.OOM}
    )

    assert monitored_action_repository.select_all() == {
        DockerEventAction.DIE,
        DockerEventAction.OOM,
    }

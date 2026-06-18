from pathlib import Path

import pytest

from app.database.monitoring_options import MonitoredEventActionRepository
from app.database.schema import init_schema
from app.models.docker_event_action import (
    DEFAULT_MONITORED_EVENT_ACTIONS,
    DockerEventAction,
)


@pytest.fixture
def monitored_action_repository(test_db_path: Path) -> MonitoredEventActionRepository:
    init_schema(test_db_path)

    return MonitoredEventActionRepository(str(test_db_path))


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

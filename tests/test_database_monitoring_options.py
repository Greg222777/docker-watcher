from app.database.monitoring_options import MonitoredEventActionRepository
from app.database.schema import init_schema
from app.models.docker_event_action import (
    DEFAULT_MONITORED_EVENT_ACTIONS,
    DockerEventAction,
)


def test_seed_defaults_seeds_default_monitored_actions(tmp_path) -> None:
    db_path = tmp_path / "docker_events.db"
    repository = MonitoredEventActionRepository(str(db_path))
    init_schema(db_path)

    repository.seed_defaults()

    assert repository.select_all() == DEFAULT_MONITORED_EVENT_ACTIONS


def test_seed_defaults_preserves_user_selection(tmp_path) -> None:
    db_path = tmp_path / "docker_events.db"
    repository = MonitoredEventActionRepository(str(db_path))
    init_schema(db_path)
    repository.seed_defaults()
    repository.replace_all({DockerEventAction.DIE, DockerEventAction.OOM})

    repository.seed_defaults()

    assert repository.select_all() == {DockerEventAction.DIE, DockerEventAction.OOM}

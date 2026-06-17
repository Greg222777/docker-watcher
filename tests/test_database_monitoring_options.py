from pathlib import Path
from uuid import uuid4

import pytest

from app.database import MonitoredEventActionRepository
from app.database.schema import init_schema
from app.models import DEFAULT_MONITORED_EVENT_ACTIONS, DockerEventAction

TEST_DIR = Path(__file__).resolve().parent


@pytest.fixture
def db_path() -> Path:
    path = TEST_DIR / f"monitoring_options_{uuid4().hex}.db"

    yield path

    try:
        if path.exists():
            path.unlink()
    except PermissionError:
        pass


def test_seed_defaults_seeds_default_monitored_actions(db_path) -> None:
    repository = MonitoredEventActionRepository(str(db_path))
    init_schema(db_path)

    repository.seed_defaults()

    assert repository.select_all() == DEFAULT_MONITORED_EVENT_ACTIONS


def test_seed_defaults_preserves_user_selection(db_path) -> None:
    repository = MonitoredEventActionRepository(str(db_path))
    init_schema(db_path)
    repository.seed_defaults()
    repository.replace_all({DockerEventAction.DIE, DockerEventAction.OOM})

    repository.seed_defaults()

    assert repository.select_all() == {DockerEventAction.DIE, DockerEventAction.OOM}

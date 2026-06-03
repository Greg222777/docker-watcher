from uuid import uuid4
from pathlib import Path

import pytest

from app.database import MonitoredEventActionRepository
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


def test_init_db_seeds_default_monitored_actions(db_path) -> None:
    repository = MonitoredEventActionRepository(str(db_path))

    repository.init_db()

    assert repository.select_all() == DEFAULT_MONITORED_EVENT_ACTIONS


def test_init_db_preserves_user_selection(db_path) -> None:
    repository = MonitoredEventActionRepository(str(db_path))
    repository.init_db()
    repository.replace_all({DockerEventAction.DIE, DockerEventAction.OOM})

    repository.init_db()

    assert repository.select_all() == {DockerEventAction.DIE, DockerEventAction.OOM}

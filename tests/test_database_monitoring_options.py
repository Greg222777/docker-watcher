import unittest
from uuid import uuid4
from pathlib import Path

from app.database import MonitoredEventActionRepository
from app.models import DEFAULT_MONITORED_EVENT_ACTIONS, DockerEventAction


TEST_DIR = Path(__file__).resolve().parent


class MonitoredEventActionRepositoryTest(unittest.TestCase):
    def setUp(self) -> None:
        self.db_path = TEST_DIR / f"monitoring_options_{uuid4().hex}.db"

    def tearDown(self) -> None:
        try:
            if self.db_path.exists():
                self.db_path.unlink()
        except PermissionError:
            pass

    def test_init_db_seeds_default_monitored_actions(self) -> None:
        repository = MonitoredEventActionRepository(str(self.db_path))

        repository.init_db()

        self.assertEqual(repository.select_all(), DEFAULT_MONITORED_EVENT_ACTIONS)

    def test_init_db_preserves_user_selection(self) -> None:
        repository = MonitoredEventActionRepository(str(self.db_path))
        repository.init_db()
        repository.replace_all({DockerEventAction.DIE, DockerEventAction.OOM})

        repository.init_db()

        self.assertEqual(
            repository.select_all(),
            {DockerEventAction.DIE, DockerEventAction.OOM},
        )


if __name__ == "__main__":
    unittest.main()

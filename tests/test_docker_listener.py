import sys
import types
import unittest
from pathlib import Path
from unittest.mock import Mock

if "docker" not in sys.modules:
    docker_module = types.ModuleType("docker")
    docker_errors_module = types.ModuleType("docker.errors")

    class APIError(Exception):
        pass

    class DockerException(Exception):
        pass

    class NotFound(Exception):
        pass

    docker_module.from_env = Mock()
    docker_errors_module.APIError = APIError
    docker_errors_module.DockerException = DockerException
    docker_errors_module.NotFound = NotFound
    sys.modules["docker"] = docker_module
    sys.modules["docker.errors"] = docker_errors_module

from app.docker_listener import DockerListener
from app.models import DockerEventAction, EventLog


TEST_DIR = Path(__file__).resolve().parent
TEST_LOG_DIR = TEST_DIR / "logs"


class DockerListenerTest(unittest.TestCase):
    def tearDown(self) -> None:
        self._clear_test_logs()

    def test_listen_handles_valid_container_event(self) -> None:
        handled_events = []
        client = self._build_client([
            {
                "Action": "die",
                "id": "abcdef1234567890",
                "time": 1710000000,
                "Actor": {
                    "Attributes": {
                        "name": "api",
                        "exitCode": "1",
                    }
                },
            }
        ])

        self._clear_test_logs()
        listener = DockerListener(
            event_handler=handled_events.append,
            watched_actions={DockerEventAction.DIE},
            client=client,
            log_dir=TEST_LOG_DIR,
        )

        listener.listen()

        self.assertEqual(len(handled_events), 1)
        self.assertEqual(handled_events[0].container_name, "api")
        self.assertEqual(handled_events[0].container_id, "abcdef1234567890")
        self.assertEqual(handled_events[0].action, "die")
        self.assertEqual(handled_events[0].exit_code, "1")
        self.assertIsNotNone(handled_events[0].log_file_path)

    def test_listen_ignores_unwatched_actions(self) -> None:
        handled_events = []
        client = self._build_client([
            {
                "Action": "start",
                "id": "abcdef1234567890",
                "Actor": {"Attributes": {"name": "api"}},
            }
        ])

        self._clear_test_logs()
        listener = DockerListener(
            event_handler=handled_events.append,
            watched_actions={"die"},
            client=client,
            log_dir=TEST_LOG_DIR,
        )

        listener.listen()

        self.assertEqual(handled_events, [])

    def test_should_handle_accepts_documented_event_action_enum(self) -> None:
        listener = DockerListener.__new__(DockerListener)
        listener.watched_actions = {DockerEventAction.DIE}

        event = EventLog(
            container_name="api",
            container_id="abcdef1234567890",
            action="die",
        )

        self.assertTrue(listener._should_handle(event))

    def test_should_handle_normalizes_health_status_actions(self) -> None:
        listener = DockerListener.__new__(DockerListener)
        listener.watched_actions = {DockerEventAction.HEALTH_STATUS}

        event = EventLog(
            container_name="api",
            container_id="abcdef1234567890",
            action="health_status: healthy",
        )

        self.assertTrue(listener._should_handle(event))

    def test_build_event_log_returns_none_for_incomplete_event(self) -> None:
        listener = DockerListener.__new__(DockerListener)

        self.assertIsNone(listener._build_event_log({"Action": "start"}))
        self.assertIsNone(listener._build_event_log({"id": "abcdef1234567890"}))

    def test_write_container_logs_uses_configured_log_dir(self) -> None:
        client = self._build_client([])
        listener = DockerListener(
            event_handler=lambda event: None,
            client=client,
        )

        self._clear_test_logs()
        listener.log_dir = TEST_LOG_DIR

        log_file_path = listener._write_container_logs(
            container_id="abcdef1234567890",
            container_name="api service",
            action="die",
            created_at="2026-06-02T10:00:00",
        )

        self.assertIsNotNone(log_file_path)
        log_file = Path(log_file_path or "")
        self.assertEqual(log_file.parent, TEST_LOG_DIR)
        self.assertEqual(log_file.read_text(encoding="utf-8"), "container logs")

    def _build_client(self, events: list[dict[str, object]]) -> Mock:
        container = Mock()
        container.logs.return_value = b"container logs"

        client = Mock()
        client.events.return_value = events
        client.containers.get.return_value = container

        return client

    def _clear_test_logs(self) -> None:
        TEST_LOG_DIR.mkdir(exist_ok=True)

        for file_path in TEST_LOG_DIR.iterdir():
            if file_path.is_file():
                file_path.unlink()


if __name__ == "__main__":
    unittest.main()

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

from app.docker_events import ContainerLogWriter, DockerEventLogBuilder


TEST_DIR = Path(__file__).resolve().parent
TEST_LOG_DIR = TEST_DIR / "logs"


class DockerEventLogBuilderTest(unittest.TestCase):
    def test_build_returns_none_for_incomplete_event(self) -> None:
        builder = DockerEventLogBuilder(
            ContainerLogWriter(self._build_client(), log_dir=TEST_LOG_DIR)
        )

        self.assertIsNone(builder.build({"Action": "start"}))
        self.assertIsNone(builder.build({"id": "abcdef1234567890"}))

    def _build_client(self) -> Mock:
        client = Mock()
        client.containers.get.return_value.logs.return_value = b"container logs"

        return client


class ContainerLogWriterTest(unittest.TestCase):
    def tearDown(self) -> None:
        self._clear_test_logs()

    def test_write_container_logs_uses_configured_log_dir(self) -> None:
        self._clear_test_logs()
        writer = ContainerLogWriter(self._build_client(), log_dir=TEST_LOG_DIR)

        log_file_path = writer.write_container_logs(
            container_id="abcdef1234567890",
            container_name="api service",
            action="die",
            created_at="2026-06-02T10:00:00",
        )

        self.assertIsNotNone(log_file_path)
        log_file = Path(log_file_path or "")
        self.assertEqual(log_file.parent, TEST_LOG_DIR)
        self.assertEqual(log_file.read_text(encoding="utf-8"), "container logs")

    def _build_client(self) -> Mock:
        container = Mock()
        container.logs.return_value = b"container logs"

        client = Mock()
        client.containers.get.return_value = container

        return client

    def _clear_test_logs(self) -> None:
        TEST_LOG_DIR.mkdir(exist_ok=True)

        for file_path in TEST_LOG_DIR.iterdir():
            if file_path.is_file():
                file_path.unlink()


if __name__ == "__main__":
    unittest.main()

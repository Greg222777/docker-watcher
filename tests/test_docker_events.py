from pathlib import Path

from app.docker_events import ContainerLogWriter, DockerEventLogBuilder
from app.models import EventLog


def test_build_returns_none_for_incomplete_event() -> None:
    builder = DockerEventLogBuilder()

    assert builder.build({"Action": "start"}) is None
    assert builder.build({"id": "abcdef1234567890"}) is None


def test_build_does_not_collect_container_logs(docker_client) -> None:
    client = docker_client()
    builder = DockerEventLogBuilder()

    event_log = builder.build({
        "Action": "start",
        "id": "abcdef1234567890",
        "Actor": {"Attributes": {"name": "api"}},
    })

    assert event_log is not None
    assert event_log.log_file_path is None
    client.containers.get.assert_not_called()


def test_write_event_log_uses_configured_log_dir(
    docker_client,
    test_log_dir,
) -> None:
    writer = ContainerLogWriter(docker_client(), log_dir=test_log_dir)
    event_log = EventLog(
        container_id="abcdef1234567890",
        container_name="api service",
        action="die",
        created_at="2026-06-02T10:00:00",
    )

    writer.write_event_log(event_log)

    assert event_log.log_file_path is not None
    log_file = Path(event_log.log_file_path)
    assert log_file.parent == test_log_dir
    assert log_file.read_text(encoding="utf-8") == "container logs"

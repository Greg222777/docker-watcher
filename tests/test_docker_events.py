from pathlib import Path

from app.docker_events import ContainerLogWriter, DockerEventLogBuilder


def test_build_returns_none_for_incomplete_event(docker_client, test_log_dir) -> None:
    builder = DockerEventLogBuilder(
        ContainerLogWriter(docker_client(), log_dir=test_log_dir)
    )

    assert builder.build({"Action": "start"}) is None
    assert builder.build({"id": "abcdef1234567890"}) is None


def test_write_container_logs_uses_configured_log_dir(
    docker_client,
    test_log_dir,
) -> None:
    writer = ContainerLogWriter(docker_client(), log_dir=test_log_dir)

    log_file_path = writer.write_container_logs(
        container_id="abcdef1234567890",
        container_name="api service",
        action="die",
        created_at="2026-06-02T10:00:00",
    )

    assert log_file_path is not None
    log_file = Path(log_file_path)
    assert log_file.parent == test_log_dir
    assert log_file.read_text(encoding="utf-8") == "container logs"

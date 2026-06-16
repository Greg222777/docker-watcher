from pathlib import Path

from app.docker_events import ContainerLogWriter, build_event_log
from app.models import EventLog


def test_build_returns_none_for_incomplete_event() -> None:
    assert build_event_log({"Action": "start"}) is None
    assert build_event_log({"id": "abcdef1234567890"}) is None


def test_build_does_not_collect_container_logs(docker_client) -> None:
    client = docker_client()

    event_log = build_event_log(
        {
            "Action": "start",
            "id": "abcdef1234567890",
            "Actor": {"Attributes": {"name": "api"}},
        }
    )

    assert event_log is not None
    assert event_log.log_file_path is None
    client.containers.get.assert_not_called()


def test_build_uses_actor_id_when_event_has_no_top_level_id() -> None:
    event_log = build_event_log(
        {
            "Type": "container",
            "Action": "exec_die",
            "Actor": {
                "ID": "d7a5aece1b9b8271f289b7337301d633a75e8851a46209800d72bf0f628b9830",
                "Attributes": {
                    "name": "filebrowser",
                    "exitCode": "0",
                },
            },
            "time": 1780958204,
        }
    )

    assert event_log is not None
    assert event_log.container_name == "filebrowser"
    assert event_log.container_id == (
        "d7a5aece1b9b8271f289b7337301d633a75e8851a46209800d72bf0f628b9830"
    )
    assert event_log.action == "exec_die"
    assert event_log.exit_code == "0"


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

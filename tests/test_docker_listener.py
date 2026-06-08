import logging
from unittest.mock import patch

from app.docker_listener import (
    DockerListener,
    _log_docker_socket_state,
    listen_to_docker_events,
)
from app.models import DockerEventAction, EventLog


def test_listen_handles_valid_container_event(
    caplog,
    docker_client,
    test_log_dir,
) -> None:
    raw_event = {
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
    client = docker_client([
        raw_event,
    ])
    listener = DockerListener(
        client=client,
        watched_docker_actions={DockerEventAction.DIE},
        log_dir=test_log_dir,
    )

    with (
        caplog.at_level(logging.INFO, logger="app.docker_listener"),
        patch("app.docker_listener.event_log_repository.save") as save_event,
        patch(
            "app.docker_listener.telegram_notifier.send_event_log"
        ) as send_event_log,
    ):
        listener.listen()

    client.events.assert_called_once_with(
        decode=True,
        filters={"type": "container"},
    )
    assert f"RAW DOCKER EVENT: {raw_event}" in caplog.text
    save_event.assert_called_once()
    send_event_log.assert_called_once()
    handled_event = save_event.call_args.args[0]
    assert handled_event.container_name == "api"
    assert handled_event.container_id == "abcdef1234567890"
    assert handled_event.action == "die"
    assert handled_event.exit_code == "1"
    assert handled_event.log_file_path is not None
    client.containers.get.assert_called_once_with("abcdef1234567890")
    assert send_event_log.call_args.args[0] is handled_event


def test_listen_logs_raw_events_before_parsing(
    caplog,
    docker_client,
    test_log_dir,
) -> None:
    raw_event = {
        "Action": "unknown",
        "id": "abcdef1234567890",
        "Actor": {"Attributes": {"name": "api"}},
    }
    client = docker_client([
        raw_event,
    ])
    listener = DockerListener(
        client=client,
        watched_docker_actions={DockerEventAction.DIE},
        log_dir=test_log_dir,
    )

    with (
        caplog.at_level(logging.INFO, logger="app.docker_listener"),
        patch("app.docker_listener.event_log_repository.save") as save_event,
        patch(
            "app.docker_listener.telegram_notifier.send_event_log"
        ) as send_event_log,
    ):
        listener.listen()

    assert f"RAW DOCKER EVENT: {raw_event}" in caplog.text
    save_event.assert_not_called()
    send_event_log.assert_not_called()


def test_listen_ignores_unwatched_actions(docker_client, test_log_dir) -> None:
    client = docker_client([
        {
            "Action": "start",
            "id": "abcdef1234567890",
            "Actor": {"Attributes": {"name": "api"}},
        }
    ])
    listener = DockerListener(
        client=client,
        watched_docker_actions={DockerEventAction.DIE},
        log_dir=test_log_dir,
    )

    with (
        patch("app.docker_listener.event_log_repository.save") as save_event,
        patch(
            "app.docker_listener.telegram_notifier.send_event_log"
        ) as send_event_log,
    ):
        listener.listen()

    save_event.assert_not_called()
    send_event_log.assert_not_called()
    client.containers.get.assert_not_called()


def test_listen_to_docker_events_logs_listener_startup(caplog) -> None:
    with (
        caplog.at_level(logging.INFO, logger="app.docker_listener"),
        patch("app.docker_listener._log_docker_socket_state") as log_socket_state,
        patch("app.docker_listener.DockerListener") as listener_class,
    ):
        listen_to_docker_events()

    log_socket_state.assert_called_once_with()
    listener_class.assert_called_once_with()
    listener_class.return_value.listen.assert_called_once_with()
    assert "Preparing Docker event listener." in caplog.text
    assert "Docker event listener created; entering event loop." in caplog.text


def test_log_docker_socket_state_warns_when_socket_is_missing(
    caplog,
    tmp_path,
) -> None:
    socket_path = tmp_path / "docker.sock"

    with caplog.at_level(logging.WARNING, logger="app.docker_listener"):
        _log_docker_socket_state(socket_path)

    assert f"Docker socket not found at {socket_path}" in caplog.text


def test_should_handle_accepts_documented_event_action_enum() -> None:
    listener = DockerListener.__new__(DockerListener)
    listener.watched_docker_actions = {DockerEventAction.DIE}
    event = EventLog(
        container_name="api",
        container_id="abcdef1234567890",
        action="die",
    )

    assert listener._should_handle(event)


def test_should_handle_normalizes_health_status_actions() -> None:
    listener = DockerListener.__new__(DockerListener)
    listener.watched_docker_actions = {DockerEventAction.HEALTH_STATUS}
    event = EventLog(
        container_name="api",
        container_id="abcdef1234567890",
        action="health_status: healthy",
    )

    assert listener._should_handle(event)

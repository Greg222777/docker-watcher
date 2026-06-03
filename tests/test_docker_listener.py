from unittest.mock import patch

from app.docker_listener import DockerListener
from app.models import DockerEventAction, EventLog


def test_listen_handles_valid_container_event(docker_client, test_log_dir) -> None:
    client = docker_client([
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

    save_event.assert_called_once()
    send_event_log.assert_called_once()
    handled_event = save_event.call_args.args[0]
    assert handled_event.container_name == "api"
    assert handled_event.container_id == "abcdef1234567890"
    assert handled_event.action == "die"
    assert handled_event.exit_code == "1"
    assert handled_event.log_file_path is not None
    assert send_event_log.call_args.args[0] is handled_event


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

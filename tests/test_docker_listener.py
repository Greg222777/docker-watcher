from pathlib import Path
from unittest.mock import Mock, patch

import app.docker_listener as docker_listener
from app.models.docker_event_action import DockerEventAction


def _docker_event(action: str) -> dict[str, object]:
    return {
        "Action": action,
        "id": "container-123",
        "Actor": {
            "Attributes": {
                "name": "api",
                "exitCode": "137",
            },
        },
        "time": 1781776800,
    }


class TestDockerEventListener:
    def test_records_watched_event_and_sends_notification(
        self,
        docker_client: Mock,
        test_log_dir: Path,
    ) -> None:
        client = docker_client([_docker_event("die")])

        with (
            patch.object(docker_listener.event_log_repository, "save") as save,
            patch.object(docker_listener, "send_event_log") as send_event_log,
        ):
            docker_listener._listen(client, {DockerEventAction.DIE}, test_log_dir)

        saved_event = save.call_args.args[0]

        assert saved_event.container_name == "api"
        assert saved_event.container_id == "container-123"
        assert saved_event.action == "die"
        assert saved_event.exit_code == "137"
        assert saved_event.log_file_path is not None
        assert Path(saved_event.log_file_path).read_text(encoding="utf-8") == (
            "container logs"
        )
        send_event_log.assert_called_once_with(saved_event)

    def test_ignores_unwatched_event(
        self,
        docker_client: Mock,
        test_log_dir: Path,
    ) -> None:
        client = docker_client([_docker_event("start")])

        with (
            patch.object(docker_listener.event_log_repository, "save") as save,
            patch.object(docker_listener, "send_event_log") as send_event_log,
        ):
            docker_listener._listen(client, {DockerEventAction.DIE}, test_log_dir)

        save.assert_not_called()
        send_event_log.assert_not_called()
        client.containers.get.assert_not_called()

    def test_uses_repository_actions_when_none_are_given(self) -> None:
        with patch.object(
            docker_listener.monitored_event_action_repository,
            "select_all",
            return_value={DockerEventAction.HEALTH_STATUS},
        ) as select_all:
            handled = docker_listener._should_handle("health_status: unhealthy", set())

        assert handled is True
        select_all.assert_called_once_with()

    def test_builds_docker_client_when_none_is_given(self, test_log_dir: Path) -> None:
        client = Mock()

        with (
            patch.object(docker_listener, "_log_docker_socket_state") as log_socket,
            patch.object(docker_listener.docker, "from_env", return_value=client),
            patch.object(docker_listener, "_listen") as listen,
        ):
            docker_listener.listen_to_docker_events(log_dir=test_log_dir)

        log_socket.assert_called_once_with()
        listen.assert_called_once_with(client, set(), test_log_dir)

from pathlib import Path
from typing import Any, Optional

import docker
from docker.errors import DockerException

from app.database import save_event, select_monitored_event_actions
from app.docker_events import ContainerLogWriter, DockerEvent, DockerEventLogBuilder
from app.docker_events.log_writer import LOG_DIR
from app.models import DockerEventAction, EventLog
from app.telegram_notifier import telegram_notifier


class DockerListener:
    def __init__(
        self,
        client: Optional[Any] = None,
        watched_actions: Optional[set[str]] = None,
        log_dir: Path = LOG_DIR,
    ) -> None:
        self.client = client or docker.from_env()
        self.watched_actions = watched_actions
        self.log_dir = log_dir
        self.log_writer = ContainerLogWriter(self.client, log_dir=log_dir)
        self.event_log_builder = DockerEventLogBuilder(self.log_writer)

    def listen(self) -> None:
        print("Docker Watcher is listening for container events...")

        for event in self.client.events(
            decode=True,
            filters={"type": "container"}
        ):
            event_log = self.event_log_builder.build(event)

            if event_log is None:
                continue

            if self._should_handle(event_log):
                self._handle_event_log(event_log)

    def _handle_event_log(self, event_log: EventLog) -> None:
        print(
            f"Docker event received: "
            f"{event_log.container_name} "
            f"{event_log.action} "
            f"{event_log.container_id[:12]}"
        )

        save_event(event_log)
        telegram_notifier.send_event_log(event_log)

    def _should_handle(self, event_log: EventLog) -> bool:
        watched_actions = self._get_watched_actions()

        if watched_actions is None:
            return True

        normalized_action = DockerEventAction.normalize(event_log.action)

        return normalized_action in {
            action.value if isinstance(action, DockerEventAction) else action
            for action in watched_actions
        }

    def _get_watched_actions(self) -> Optional[set[str]]:
        if self.watched_actions is not None:
            return self.watched_actions

        return {
            action.value
            for action in select_monitored_event_actions()
        }

    def _build_event_log(self, event: DockerEvent) -> Optional[EventLog]:
        return self.event_log_builder.build(event)

    def _extract_exit_code(self, attributes: dict[str, Any]) -> Optional[str]:
        return self.event_log_builder.extract_exit_code(attributes)

    def _extract_created_at(self, event: DockerEvent) -> str:
        return self.event_log_builder.extract_created_at(event)

    def _write_container_logs(
        self,
        container_id: str,
        container_name: str,
        action: str,
        created_at: str
    ) -> Optional[str]:
        self.log_writer.log_dir = self.log_dir

        return self.log_writer.write_container_logs(
            container_id=container_id,
            container_name=container_name,
            action=action,
            created_at=created_at,
        )

    def _build_log_filename(
        self,
        container_name: str,
        container_id: str,
        action: str,
        created_at: str
    ) -> str:
        self.log_writer.log_dir = self.log_dir

        return self.log_writer.build_log_filename(
            container_name=container_name,
            container_id=container_id,
            action=action,
            created_at=created_at,
        )

    def _sanitize_filename_part(self, value: str) -> str:
        self.log_writer.log_dir = self.log_dir

        return self.log_writer.sanitize_filename_part(value)


def listen_to_docker_events() -> None:
    try:
        DockerListener().listen()
    except DockerException as error:
        print(f"Could not listen to Docker events: {error}")

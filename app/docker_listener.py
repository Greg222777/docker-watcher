from pathlib import Path
from typing import Any, Callable, Optional

import docker
from docker.errors import DockerException

from app.actions import handle_event_log
from app.docker_events import DockerClient, DockerEvent, DockerEventLogBuilder, DockerLogCollector
from app.docker_events.log_collector import LOG_DIR
from app.models import DockerEventAction, EventLog


EventHandler = Callable[[EventLog], None]
WatchedAction = str | DockerEventAction
WatchedActionProvider = Callable[[], set[WatchedAction]]


class DockerListener:
    def __init__(
        self,
        event_handler: EventHandler = handle_event_log,
        watched_actions: Optional[set[WatchedAction]] = None,
        watched_action_provider: Optional[WatchedActionProvider] = None,
        client: Optional[DockerClient] = None,
        log_dir: Path = LOG_DIR,
    ) -> None:
        self.client = client or docker.from_env()
        self.event_handler = event_handler
        self.watched_actions = watched_actions
        self.watched_action_provider = watched_action_provider
        self.log_dir = log_dir
        self.log_collector = DockerLogCollector(self.client, log_dir=log_dir)
        self.event_log_builder = DockerEventLogBuilder(self.log_collector)

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
                self.event_handler(event_log)

    def _should_handle(self, event_log: EventLog) -> bool:
        watched_actions = self._get_watched_actions()

        if watched_actions is None:
            return True

        normalized_action = DockerEventAction.normalize(event_log.action)

        return normalized_action in {
            action.value if isinstance(action, DockerEventAction) else action
            for action in watched_actions
        }

    def _get_watched_actions(self) -> Optional[set[WatchedAction]]:
        if self.watched_actions is not None:
            return self.watched_actions

        if self.watched_action_provider is not None:
            return self.watched_action_provider()

        from app.database import select_monitored_event_actions

        return select_monitored_event_actions()

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
        self.log_collector.log_dir = self.log_dir

        return self.log_collector.write_container_logs(
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
        self.log_collector.log_dir = self.log_dir

        return self.log_collector.build_log_filename(
            container_name=container_name,
            container_id=container_id,
            action=action,
            created_at=created_at,
        )

    def _sanitize_filename_part(self, value: str) -> str:
        self.log_collector.log_dir = self.log_dir

        return self.log_collector.sanitize_filename_part(value)


def listen_to_docker_events() -> None:
    try:
        DockerListener().listen()
    except DockerException as error:
        print(f"Could not listen to Docker events: {error}")

from pathlib import Path
from typing import Any, Optional

import docker
from docker.errors import DockerException

from app.database import event_log_repository, monitored_event_action_repository
from app.docker_events import ContainerLogWriter, DockerEventLogBuilder
from app.docker_events.log_writer import LOG_DIR
from app.models import DockerEventAction, EventLog, WatchedDockerActions
from app.telegram_notifier import telegram_notifier


class DockerListener:
    def __init__(
        self,
        client: Optional[Any] = None,
        watched_docker_actions: WatchedDockerActions = frozenset(),
        log_dir: Path = LOG_DIR,
    ) -> None:
        self.client = client or docker.from_env()
        self.watched_docker_actions = watched_docker_actions
        self.log_writer = ContainerLogWriter(self.client, log_dir=log_dir)
        self.event_log_builder = DockerEventLogBuilder()

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

        self.log_writer.write_event_log(event_log)
        event_log_repository.save(event_log)
        telegram_notifier.send_event_log(event_log)

    def _should_handle(self, event_log: EventLog) -> bool:
        watched_docker_actions = self._get_watched_docker_actions()

        return any(
            action.matches(event_log.action)
            for action in watched_docker_actions
        )

    def _get_watched_docker_actions(self) -> WatchedDockerActions:
        if self.watched_docker_actions:
            return self.watched_docker_actions

        return monitored_event_action_repository.select_all()


def listen_to_docker_events() -> None:
    try:
        DockerListener().listen()
    except DockerException as error:
        print(f"Could not listen to Docker events: {error}")

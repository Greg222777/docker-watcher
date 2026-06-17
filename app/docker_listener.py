import logging
from collections.abc import Collection
from pathlib import Path
from typing import Any

import docker
from docker.errors import DockerException

from app.database import event_log_repository, monitored_event_action_repository
from app.docker_events import build_event_log, write_event_log
from app.docker_events.log_writer import LOG_DIR
from app.models import DockerEventAction, EventLog
from app.telegram_notifier import telegram_notifier

logger = logging.getLogger(__name__)
DOCKER_SOCKET_PATH = Path("/var/run/docker.sock")


class DockerListener:
    def __init__(
        self,
        client: Any | None = None,
        watched_docker_actions: Collection[DockerEventAction] = frozenset(),
        log_dir: Path = LOG_DIR,
    ) -> None:
        self.client = client or docker.from_env()
        self.watched_docker_actions = watched_docker_actions
        self.log_dir = log_dir

    def listen(self) -> None:
        logger.info("Docker Watcher is listening for container events...")

        for event in self.client.events(decode=True, filters={"type": "container"}):
            logger.info("RAW DOCKER EVENT: %s", event)
            event_log = build_event_log(event)

            if event_log is None:
                continue

            if self._should_handle(event_log):
                self._handle_event_log(event_log)

    def _handle_event_log(self, event_log: EventLog) -> None:
        logger.info(
            "Docker event received: %s %s %s",
            event_log.container_name,
            event_log.action,
            event_log.container_id,
        )

        write_event_log(self.client, event_log, log_dir=self.log_dir)
        event_log_repository.save(event_log)
        telegram_notifier.send_event_log(event_log)

    def _should_handle(self, event_log: EventLog) -> bool:
        watched_docker_actions = self._get_watched_docker_actions()

        return any(
            action.matches(event_log.action) for action in watched_docker_actions
        )

    def _get_watched_docker_actions(self) -> Collection[DockerEventAction]:
        if self.watched_docker_actions:
            return self.watched_docker_actions

        return monitored_event_action_repository.select_all()


def listen_to_docker_events() -> None:
    try:
        logger.info("Preparing Docker event listener.")
        _log_docker_socket_state()
        listener = DockerListener()
        logger.info("Docker event listener created; entering event loop.")
        listener.listen()
    except DockerException as error:
        logger.error("Could not listen to Docker events: %s", error)


def _log_docker_socket_state(socket_path: Path = DOCKER_SOCKET_PATH) -> None:
    try:
        if not socket_path.exists():
            logger.warning(
                "Docker socket not found at %s. Mount "
                "/var/run/docker.sock:/var/run/docker.sock in Docker Compose.",
                socket_path,
            )
            return

        socket_stat = socket_path.stat()
    except OSError as error:
        logger.warning("Could not inspect Docker socket at %s: %s", socket_path, error)
        return

    logger.info(
        "Docker socket found at %s (socket=%s, mode=%s).",
        socket_path,
        socket_path.is_socket(),
        oct(socket_stat.st_mode & 0o777),
    )

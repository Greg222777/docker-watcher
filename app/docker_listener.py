import logging
from pathlib import Path
from typing import Any

import docker
from docker.errors import DockerException

from app.database import event_log_repository, monitored_event_action_repository
from app.docker_events.event_log_builder import build_event_log
from app.docker_events.log_writer import LOG_DIR, write_event_log
from app.models.docker_event_action import DockerEventAction
from app.models.event_log import EventLog
from app.telegram import send_event_notification

logger = logging.getLogger(__name__)
DOCKER_SOCKET_PATH = Path("/var/run/docker.sock")


def listen_to_docker_events(
    client: Any | None = None,
    watched_docker_actions: set[DockerEventAction] | None = None,
    log_dir: Path = LOG_DIR,
) -> None:
    try:
        logger.info("Preparing Docker event listener.")
        _log_docker_socket_state()
        docker_client = client or docker.from_env()
        logger.info("Docker event listener created; entering event loop.")
        _listen(docker_client, watched_docker_actions or set(), log_dir)
    except DockerException as error:
        logger.error("Could not listen to Docker events: %s", error)


def _listen(
    client: Any,
    watched_docker_actions: set[DockerEventAction],
    log_dir: Path,
) -> None:
    logger.info("Docker Watcher is listening for container events...")

    for event in client.events(decode=True, filters={"type": "container"}):
        logger.info("RAW DOCKER EVENT: %s", event)
        event_log = build_event_log(event)

        if event_log is not None and _should_handle(
            event_log.action,
            watched_docker_actions,
        ):
            _handle_event_log(client, event_log, log_dir)


def _handle_event_log(client: Any, event_log: EventLog, log_dir: Path) -> None:
    logger.info(
        "Docker event received: %s %s %s",
        event_log.container_name,
        event_log.action,
        event_log.container_id,
    )

    write_event_log(client, event_log, log_dir=log_dir)
    event_log_repository.save(event_log)
    send_event_notification(event_log)


def _should_handle(
    action: str,
    watched_docker_actions: set[DockerEventAction],
) -> bool:
    watched_actions = (
        watched_docker_actions or monitored_event_action_repository.select_all()
    )

    return any(watched_action.matches(action) for watched_action in watched_actions)


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

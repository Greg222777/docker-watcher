from datetime import datetime
from pathlib import Path
import re
from typing import Any, Callable, Optional, Protocol

import docker
from docker.errors import APIError, DockerException, NotFound

from app.actions import handle_event_log
from app.models import DockerEventAction, EventLog


DockerEvent = dict[str, Any]
EventHandler = Callable[[EventLog], None]
WatchedAction = str | DockerEventAction
WatchedActionProvider = Callable[[], set[WatchedAction]]
LOG_DIR = Path("/data/logs")
LOG_TAIL_LINES = 200


class DockerClient(Protocol):
    def events(self, **kwargs: Any) -> Any:
        ...


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

    def listen(self) -> None:
        print("Docker Watcher is listening for container events...")

        for event in self.client.events(
            decode=True,
            filters={"type": "container"}
        ):
            event_log = self._build_event_log(event)

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
        action = event.get("Action") or event.get("status")
        container_id = event.get("id")

        if not action or not container_id:
            return None

        attributes = event.get("Actor", {}).get("Attributes", {})
        container_name = attributes.get("name", "unknown")
        created_at = self._extract_created_at(event)

        return EventLog(
            container_name=container_name,
            container_id=container_id,
            action=action,
            exit_code=self._extract_exit_code(attributes),
            log_file_path=self._write_container_logs(
                container_id=container_id,
                container_name=container_name,
                action=action,
                created_at=created_at,
            ),
            created_at=created_at,
        )

    def _extract_exit_code(self, attributes: dict[str, Any]) -> Optional[str]:
        return (
            attributes.get("exitCode")
            or attributes.get("exit_code")
            or attributes.get("ExitCode")
        )

    def _extract_created_at(self, event: DockerEvent) -> str:
        event_timestamp = event.get("time")

        if event_timestamp is None:
            return datetime.now().isoformat()

        return datetime.fromtimestamp(event_timestamp).isoformat()

    def _write_container_logs(
        self,
        container_id: str,
        container_name: str,
        action: str,
        created_at: str
    ) -> Optional[str]:
        try:
            container = self.client.containers.get(container_id)
            logs = container.logs(tail=LOG_TAIL_LINES, timestamps=True)
        except NotFound:
            print(f"Could not collect logs: container {container_id[:12]} not found.")
            return None
        except APIError as error:
            print(f"Could not collect logs for {container_id[:12]}: {error}")
            return None

        try:
            self.log_dir.mkdir(parents=True, exist_ok=True)

            log_file_path = self.log_dir / self._build_log_filename(
                container_name=container_name,
                container_id=container_id,
                action=action,
                created_at=created_at,
            )

            log_file_path.write_text(
                logs.decode("utf-8", errors="replace"),
                encoding="utf-8"
            )
        except OSError as error:
            print(f"Could not write logs for {container_id[:12]}: {error}")
            return None

        return str(log_file_path)

    def _build_log_filename(
        self,
        container_name: str,
        container_id: str,
        action: str,
        created_at: str
    ) -> str:
        safe_name = self._sanitize_filename_part(container_name)
        safe_action = self._sanitize_filename_part(action)
        safe_timestamp = self._sanitize_filename_part(created_at)

        return f"{safe_timestamp}_{safe_name}_{safe_action}_{container_id[:12]}.txt"

    def _sanitize_filename_part(self, value: str) -> str:
        return re.sub(r"[^a-zA-Z0-9_.-]+", "-", value).strip("-") or "unknown"


def listen_to_docker_events() -> None:
    try:
        DockerListener().listen()
    except DockerException as error:
        print(f"Could not listen to Docker events: {error}")

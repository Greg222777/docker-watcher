import logging
import re
from pathlib import Path
from typing import Any

from app.config import LOG_DIR
from app.models import EventLog

docker_errors: Any
try:
    from docker import errors as imported_docker_errors
except ModuleNotFoundError:

    class DockerAPIError(Exception):
        pass

    class DockerNotFound(Exception):
        pass

    class DockerErrors:
        APIError = DockerAPIError
        NotFound = DockerNotFound

    docker_errors = DockerErrors()
else:
    docker_errors = imported_docker_errors


LOG_TAIL_LINES = 200
logger = logging.getLogger(__name__)


class ContainerLogWriter:
    def __init__(
        self,
        client: Any,
        log_dir: Path = LOG_DIR,
        tail_lines: int = LOG_TAIL_LINES,
    ) -> None:
        self.client = client
        self.log_dir = log_dir
        self.tail_lines = tail_lines

    def write_event_log(self, event_log: EventLog) -> None:
        event_log.log_file_path = self._write_container_logs(
            container_id=event_log.container_id,
            container_name=event_log.container_name,
            action=event_log.action,
            created_at=event_log.created_at,
        )

    def _write_container_logs(
        self, container_id: str, container_name: str, action: str, created_at: str
    ) -> str | None:
        try:
            container = self.client.containers.get(container_id)
            logs = container.logs(tail=self.tail_lines, timestamps=True)
        except docker_errors.NotFound:
            logger.warning(
                "Could not collect logs: container %s not found.",
                container_id[:12],
            )
            return None
        except docker_errors.APIError as error:
            logger.warning(
                "Could not collect logs for %s: %s",
                container_id[:12],
                error,
            )
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
                logs.decode("utf-8", errors="replace"), encoding="utf-8"
            )
        except OSError as error:
            logger.error(
                "Could not write logs for %s: %s",
                container_id[:12],
                error,
            )
            return None

        return str(log_file_path)

    def _build_log_filename(
        self, container_name: str, container_id: str, action: str, created_at: str
    ) -> str:
        safe_name = self._sanitize_filename_part(container_name)
        safe_action = self._sanitize_filename_part(action)
        safe_timestamp = self._sanitize_filename_part(created_at)

        return f"{safe_timestamp}_{safe_name}_{safe_action}_{container_id[:12]}.txt"

    def _sanitize_filename_part(self, value: str) -> str:
        return re.sub(r"[^a-zA-Z0-9_.-]+", "-", value).strip("-") or "unknown"

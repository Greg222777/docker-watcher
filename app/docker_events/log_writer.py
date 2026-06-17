import logging
import re
from pathlib import Path
from typing import Any

from docker.errors import APIError, NotFound

from app.config import LOG_DIR
from app.models import EventLog

LOG_TAIL_LINES = 200
logger = logging.getLogger(__name__)


def write_event_log(
    client: Any,
    event_log: EventLog,
    log_dir: Path = LOG_DIR,
    tail_lines: int = LOG_TAIL_LINES,
) -> None:
    # Docker can remove a container before we get a chance to read its logs.
    try:
        container = client.containers.get(event_log.container_id)
        logs = container.logs(tail=tail_lines, timestamps=True)
    except NotFound:
        logger.warning(
            "Could not collect logs: container %s not found.",
            event_log.container_id,
        )
        return
    except APIError as error:
        logger.warning(
            "Could not collect logs for %s: %s",
            event_log.container_id,
            error,
        )
        return

    # Only mark the event with a log path after the file is safely written.
    try:
        log_dir.mkdir(parents=True, exist_ok=True)

        log_file_path = log_dir / _build_log_filename(
            container_name=event_log.container_name,
            container_id=event_log.container_id,
            action=event_log.action,
            created_at=event_log.created_at,
        )

        log_file_path.write_text(
            logs.decode("utf-8", errors="replace"), encoding="utf-8"
        )
        event_log.log_file_path = str(log_file_path)
    except OSError as error:
        logger.error(
            "Could not write logs for %s: %s",
            event_log.container_id,
            error,
        )


def _build_log_filename(
    container_name: str, container_id: str, action: str, created_at: str
) -> str:
    safe_name = _sanitize_filename_part(container_name)
    safe_action = _sanitize_filename_part(action)
    safe_timestamp = _sanitize_filename_part(created_at)

    return f"{safe_timestamp}_{safe_name}_{safe_action}_{container_id}.txt"


def _sanitize_filename_part(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_.-]+", "-", value).strip("-") or "unknown"

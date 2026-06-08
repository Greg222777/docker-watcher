from pathlib import Path
import re
from typing import Optional

from app.config import LOG_DIR

try:
    from docker.errors import APIError, NotFound
except ModuleNotFoundError:
    class APIError(Exception):
        pass

    class NotFound(Exception):
        pass


LOG_TAIL_LINES = 200


class ContainerLogWriter:
    def __init__(
        self,
        client: object,
        log_dir: Path = LOG_DIR,
        tail_lines: int = LOG_TAIL_LINES,
    ) -> None:
        self.client = client
        self.log_dir = log_dir
        self.tail_lines = tail_lines

    def write_container_logs(
        self,
        container_id: str,
        container_name: str,
        action: str,
        created_at: str
    ) -> Optional[str]:
        try:
            container = self.client.containers.get(container_id)
            logs = container.logs(tail=self.tail_lines, timestamps=True)
        except NotFound:
            print(f"Could not collect logs: container {container_id[:12]} not found.")
            return None
        except APIError as error:
            print(f"Could not collect logs for {container_id[:12]}: {error}")
            return None

        try:
            self.log_dir.mkdir(parents=True, exist_ok=True)

            log_file_path = self.log_dir / self.build_log_filename(
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

    def build_log_filename(
        self,
        container_name: str,
        container_id: str,
        action: str,
        created_at: str
    ) -> str:
        safe_name = self.sanitize_filename_part(container_name)
        safe_action = self.sanitize_filename_part(action)
        safe_timestamp = self.sanitize_filename_part(created_at)

        return f"{safe_timestamp}_{safe_name}_{safe_action}_{container_id[:12]}.txt"

    def sanitize_filename_part(self, value: str) -> str:
        return re.sub(r"[^a-zA-Z0-9_.-]+", "-", value).strip("-") or "unknown"

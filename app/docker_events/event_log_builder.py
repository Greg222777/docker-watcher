from datetime import datetime
from typing import Optional

from app.docker_events.log_collector import DockerLogCollector
from app.docker_events.types import DockerEvent
from app.models import EventLog


class DockerEventLogBuilder:
    def __init__(self, log_collector: DockerLogCollector) -> None:
        self.log_collector = log_collector

    def build(self, event: DockerEvent) -> Optional[EventLog]:
        action = event.get("Action") or event.get("status")
        container_id = event.get("id")

        if not action or not container_id:
            return None

        attributes = event.get("Actor", {}).get("Attributes", {})
        container_name = attributes.get("name", "unknown")
        created_at = self.extract_created_at(event)

        return EventLog(
            container_name=container_name,
            container_id=container_id,
            action=action,
            exit_code=self.extract_exit_code(attributes),
            log_file_path=self.log_collector.write_container_logs(
                container_id=container_id,
                container_name=container_name,
                action=action,
                created_at=created_at,
            ),
            created_at=created_at,
        )

    def extract_exit_code(self, attributes: dict[str, object]) -> Optional[str]:
        exit_code = (
            attributes.get("exitCode")
            or attributes.get("exit_code")
            or attributes.get("ExitCode")
        )

        if exit_code is None:
            return None

        return str(exit_code)

    def extract_created_at(self, event: DockerEvent) -> str:
        event_timestamp = event.get("time")

        if event_timestamp is None:
            return datetime.now().isoformat()

        return datetime.fromtimestamp(event_timestamp).isoformat()

from datetime import datetime

from app.docker_events.types import DockerEvent
from app.models import EventLog


class DockerEventLogBuilder:
    def build(self, event: DockerEvent) -> EventLog | None:
        action = event.get("Action") or event.get("status")
        actor = event.get("Actor", {})
        container_id = event.get("id") or actor.get("ID")

        if not action or not container_id:
            return None

        attributes = actor.get("Attributes", {})
        container_name = attributes.get("name", "unknown")
        created_at = self.extract_created_at(event)

        return EventLog(
            container_name=container_name,
            container_id=container_id,
            action=action,
            exit_code=self.extract_exit_code(attributes),
            created_at=created_at,
        )

    def extract_exit_code(self, attributes: dict[str, object]) -> str | None:
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

from datetime import datetime
from typing import Any

from app.models import EventLog


def build_event_log(event: dict[str, Any]) -> EventLog | None:
    action = event.get("Action") or event.get("status")
    actor = event.get("Actor", {})
    container_id = event.get("id") or actor.get("ID")

    if not action or not container_id:
        return None

    attributes = actor.get("Attributes", {})
    container_name = attributes.get("name", "unknown")
    exit_code = (
        attributes.get("exitCode")
        or attributes.get("exit_code")
        or attributes.get("ExitCode")
    )
    event_timestamp = event.get("time")

    return EventLog(
        container_name=container_name,
        container_id=container_id,
        action=action,
        exit_code=None if exit_code is None else str(exit_code),
        created_at=(
            datetime.now().isoformat()
            if event_timestamp is None
            else datetime.fromtimestamp(event_timestamp).isoformat()
        ),
    )

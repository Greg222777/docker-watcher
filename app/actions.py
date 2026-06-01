from app.database import save_event
from app.models import EventLog
from app.telegram_notifier import send_event_log


def handle_event_log(event: EventLog) -> None:
    print(
        f"Docker event received: "
        f"{event.container_name} {event.action} {event.container_id[:12]}"
    )

    save_event(event)
    send_event_log(event)

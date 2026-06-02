from app.database.event_logs import DB_PATH, EventLogRepository
from app.database.monitoring_options import MonitoredEventActionRepository
from app.models import DockerEventAction, EventLog


event_log_repository = EventLogRepository()
monitored_event_action_repository = MonitoredEventActionRepository()


def _sync_repository_paths() -> None:
    monitored_event_action_repository.db_path = event_log_repository.db_path


def init_db() -> None:
    _sync_repository_paths()
    event_log_repository.init_db()
    monitored_event_action_repository.init_db()


def save_event(event: EventLog) -> None:
    event_log_repository.save(event)


def delete_event(event_id: int) -> None:
    event_log_repository.delete(event_id)


def delete_all_events() -> None:
    event_log_repository.delete_all()


def select_events_between(
    start_timestamp: str,
    end_timestamp: str
) -> list[EventLog]:
    return event_log_repository.select_between(start_timestamp, end_timestamp)


def select_all_events() -> list[EventLog]:
    return event_log_repository.select_all()


def select_monitored_event_actions() -> set[DockerEventAction]:
    _sync_repository_paths()
    return monitored_event_action_repository.select_all()


def replace_monitored_event_actions(actions: set[DockerEventAction]) -> None:
    _sync_repository_paths()
    monitored_event_action_repository.replace_all(actions)

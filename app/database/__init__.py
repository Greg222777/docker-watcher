from app.database.event_logs import EventLogRepository
from app.database.monitoring_options import MonitoredEventActionRepository

event_log_repository = EventLogRepository()
monitored_event_action_repository = MonitoredEventActionRepository()

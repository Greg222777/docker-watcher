from dataclasses import dataclass


@dataclass(frozen=True)
class TelegramOptions:
    receive_daily_status: bool = False
    daily_status_time: str = ""
    receive_event_notifications: bool = True

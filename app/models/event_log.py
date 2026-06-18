from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class EventLog:
    container_name: str
    container_id: str
    action: str
    exit_code: str | None = None
    log_file_path: str | None = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    id: int | None = None

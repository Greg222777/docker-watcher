import os
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

import app.web_server as web_server  # noqa: E402
from app.database import (  # noqa: E402
    EventLogRepository,
    MonitoredEventActionRepository,
)
from app.database.schema import init_schema  # noqa: E402
from app.models.event_log import EventLog  # noqa: E402
from app.web_server import run_web_server  # noqa: E402

PREVIEW_DIR = Path("data/mock-preview").resolve()
DB_PATH = PREVIEW_DIR / "docker_events.db"
LOG_DIR = PREVIEW_DIR / "logs"


def main() -> None:
    event_log_repository = EventLogRepository(str(DB_PATH))
    monitoring_repository = MonitoredEventActionRepository(str(DB_PATH))

    web_server.LOG_DIR = LOG_DIR
    web_server.event_log_repository = event_log_repository
    web_server.monitored_event_action_repository = monitoring_repository
    seed_mock_data(event_log_repository, monitoring_repository)

    os.environ.setdefault("WEB_PORT", "8000")
    web_server.WEB_PORT = int(os.environ["WEB_PORT"])

    print("Mock web preview loaded with sample Docker events.")
    run_web_server()


def seed_mock_data(
    event_log_repository: EventLogRepository,
    monitoring_repository: MonitoredEventActionRepository,
) -> None:
    PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    init_schema(DB_PATH)
    monitoring_repository.seed_defaults()
    event_log_repository.delete_all()
    clear_logs()

    now = datetime.now().replace(microsecond=0)
    events = [
        build_event(
            id=1,
            container_name="docker-watcher",
            container_id="f4a7d9b2138c0d4a5e6f778899001122",
            action="start",
            exit_code=None,
            created_at=now - timedelta(minutes=2),
            log_body=[
                "Docker Watcher is listening for container events...",
                "Web UI is available on port 8000.",
            ],
        ),
        build_event(
            id=2,
            container_name="api-service",
            container_id="a18bc2d384ef5678901234567890abcd",
            action="die",
            exit_code="1",
            created_at=now - timedelta(minutes=8),
            log_body=[
                "Starting API service",
                "Unhandled RuntimeError: database connection failed",
                "Container exited with code 1",
            ],
        ),
        build_event(
            id=3,
            container_name="postgres",
            container_id="9f8e7d6c5b4a32100123456789abcdef",
            action="health_status: healthy",
            exit_code=None,
            created_at=now - timedelta(minutes=17),
            log_body=[
                "database system is ready to accept connections",
            ],
        ),
        build_event(
            id=4,
            container_name="redis-cache",
            container_id="1234567890abcdef1234567890abcdef",
            action="restart",
            exit_code="0",
            created_at=now - timedelta(hours=1),
            log_body=None,
        ),
        build_event(
            id=5,
            container_name="worker-storage",
            container_id="b8d7a4f1c9e24001a88bb66123cc9900",
            action="die",
            exit_code="1",
            created_at=datetime.fromisoformat("2026-06-10T14:23:16"),
            log_body=[
                "2026-06-10T14:17:03.124Z INFO  Starting application...",
                "2026-06-10T14:17:04.451Z INFO  Connected to database",
                "2026-06-10T14:17:05.832Z INFO  Initializing log storage",
                "2026-06-10T14:17:06.104Z INFO  Processing scheduled tasks",
                "",
                "2026-06-10T14:23:11.887Z WARN  Failed to rotate log file: no space left on device",
                "2026-06-10T14:23:12.014Z WARN  Disk usage critical: 99%",
                "",
                '2026-06-10T14:23:15.223Z ERROR Failed to write file "/app/data/cache/session_421.tmp"',
                "Error: ENOSPC: no space left on device, write",
                "",
                "2026-06-10T14:23:15.224Z ERROR Failed to save application state",
                "Error: ENOSPC: no space left on device",
                "",
                "2026-06-10T14:23:16.118Z ERROR Database write failed",
                "SQLITE_FULL: database or disk is full",
                "",
                "2026-06-10T14:23:16.542Z FATAL Unable to continue operation",
                "Reason: persistent storage unavailable",
                "",
                "2026-06-10T14:23:16.543Z INFO  Shutting down...",
                "2026-06-10T14:23:16.712Z ERROR Process terminated",
            ],
        ),
    ]

    for event in events:
        event_log_repository.save(event)


def build_event(
    id: int,
    container_name: str,
    container_id: str,
    action: str,
    exit_code: str | None,
    created_at: datetime,
    log_body: list[str] | None,
) -> EventLog:
    log_file_path = None
    created_at_value = created_at.isoformat()

    if log_body is not None:
        log_file_path = str(
            write_log_file(
                event_id=id,
                container_name=container_name,
                action=action,
                created_at=created_at_value,
                lines=log_body,
            )
        )

    return EventLog(
        id=id,
        container_name=container_name,
        container_id=container_id,
        action=action,
        exit_code=exit_code,
        log_file_path=log_file_path,
        created_at=created_at_value,
    )


def write_log_file(
    event_id: int,
    container_name: str,
    action: str,
    created_at: str,
    lines: list[str],
) -> Path:
    filename = f"{event_id:02d}_{sanitize(container_name)}_{sanitize(action)}.log"
    log_file = LOG_DIR / filename
    timestamped_lines = [f"{created_at} {line}" for line in lines]
    log_file.write_text("\n".join(timestamped_lines) + "\n", encoding="utf-8")
    return log_file


def sanitize(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_.-]+", "-", value).strip("-") or "unknown"


def clear_logs() -> None:
    for log_file in LOG_DIR.iterdir():
        if log_file.is_file():
            log_file.unlink()


if __name__ == "__main__":
    main()

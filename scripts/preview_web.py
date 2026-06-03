import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from app import database
from app.models import EventLog
from app.web_server import run_web_server
import app.web_server as web_server


PREVIEW_DIR = Path("data/mock-preview").resolve()
DB_PATH = PREVIEW_DIR / "docker_events.db"
LOG_DIR = PREVIEW_DIR / "logs"


def main() -> None:
    seed_mock_data()

    database.event_log_repository.db_path = str(DB_PATH)
    web_server.LOG_DIR = LOG_DIR

    os.environ.setdefault("WEB_PORT", "8000")
    web_server.WEB_PORT = int(os.environ["WEB_PORT"])

    print("Mock web preview loaded with sample Docker events.")
    run_web_server()


def seed_mock_data() -> None:
    PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    database.event_log_repository.db_path = str(DB_PATH)
    database.monitored_event_action_repository.db_path = str(DB_PATH)
    database.event_log_repository.init_db()
    database.monitored_event_action_repository.init_db()
    database.event_log_repository.delete_all()
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
    ]

    for event in events:
        database.event_log_repository.save(event)


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
        log_file_path = str(write_log_file(
            id=id,
            container_name=container_name,
            action=action,
            created_at=created_at_value,
            lines=log_body,
        ))

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
    id: int,
    container_name: str,
    action: str,
    created_at: str,
    lines: list[str],
) -> Path:
    filename = f"{id:02d}_{sanitize(container_name)}_{sanitize(action)}.log"
    log_file = LOG_DIR / filename
    timestamped_lines = [f"{created_at} {line}" for line in lines]
    log_file.write_text("\n".join(timestamped_lines) + "\n", encoding="utf-8")
    return log_file


def sanitize(value: str) -> str:
    return "".join(
        character if character.isalnum() or character in "._-" else "-"
        for character in value
    ).strip("-") or "unknown"


def clear_logs() -> None:
    for log_file in LOG_DIR.iterdir():
        if log_file.is_file():
            log_file.unlink()


if __name__ == "__main__":
    main()

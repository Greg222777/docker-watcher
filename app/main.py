import logging
import os
from threading import Thread

from app.config import DB_PATH
from app.cron_telegram_status import sync_schedule as sync_telegram_status_schedule
from app.database import monitored_event_action_repository
from app.database.schema import init_schema
from app.docker_listener import listen_to_docker_events
from app.web_server import run_web_server

logger = logging.getLogger(__name__)


def main() -> None:
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO").upper(),
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )
    logger.info("Docker Watcher startup begins.")
    logger.info("Initializing database schema.")
    init_schema(DB_PATH)
    logger.info("Initializing default monitoring options.")
    monitored_event_action_repository.seed_defaults()
    logger.info("Starting Docker Watcher web UI thread.")
    Thread(target=run_web_server, daemon=True).start()
    logger.info("Starting Telegram daily status cron.")
    sync_telegram_status_schedule()
    logger.info("Starting Docker event listener.")
    listen_to_docker_events()


if __name__ == "__main__":
    main()

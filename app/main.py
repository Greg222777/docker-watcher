import logging

from app.config import DB_PATH
from app.database import monitored_event_action_repository
from app.database.schema import run_migrations
from app.docker_listener import listen_to_docker_events
from app.logging_config import configure_logging
from app.web_server import start_web_server

logger = logging.getLogger(__name__)


def main() -> None:
    configure_logging()
    logger.info("Docker Watcher startup begins.")
    logger.info("Applying database migrations.")
    run_migrations(DB_PATH)
    logger.info("Initializing default monitoring options.")
    monitored_event_action_repository.seed_defaults()
    logger.info("Starting Docker Watcher web UI thread.")
    start_web_server()
    logger.info("Starting Docker event listener.")
    listen_to_docker_events()


if __name__ == "__main__":
    main()

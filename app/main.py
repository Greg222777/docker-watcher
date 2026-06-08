import logging

from app.database import event_log_repository, monitored_event_action_repository
from app.docker_listener import listen_to_docker_events
from app.logging_config import configure_logging
from app.web_server import start_web_server


logger = logging.getLogger(__name__)


def main() -> None:
    configure_logging()
    logger.info("Docker Watcher startup begins.")
    logger.info("Initializing event log database.")
    event_log_repository.init_db()
    logger.info("Initializing monitoring options database.")
    monitored_event_action_repository.init_db()
    logger.info("Starting Docker Watcher web UI thread.")
    start_web_server()
    logger.info("Starting Docker event listener.")
    listen_to_docker_events()


if __name__ == "__main__":
    main()

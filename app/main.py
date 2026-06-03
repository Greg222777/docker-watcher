from app.database import event_log_repository, monitored_event_action_repository
from app.docker_listener import listen_to_docker_events
from app.web_server import start_web_server


def main() -> None:
    event_log_repository.init_db()
    monitored_event_action_repository.init_db()
    start_web_server()
    listen_to_docker_events()


if __name__ == "__main__":
    main()

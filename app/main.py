from app.database import init_db
from app.docker_listener import listen_to_docker_events
from app.web_server import start_web_server


def main() -> None:
    init_db()
    start_web_server()
    listen_to_docker_events()


if __name__ == "__main__":
    main()

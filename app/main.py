from app.database import init_db
from app.docker_listener import listen_to_docker_events


def main() -> None:
    init_db()
    listen_to_docker_events()


if __name__ == "__main__":
    main()

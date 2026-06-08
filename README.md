# Docker Watcher 🐳

Docker Watcher monitors Docker container events, stores them locally in SQLite,
captures recent container logs, and can send Telegram notifications when watched
events happen.

## Features ✨

- Watches Docker container events.
- Stores event history locally in SQLite.
- Captures recent container logs for recorded events.
- Sends optional Telegram notifications.
- Provides a Flask web UI.
- Supports configurable storage and log level.
- Runs with Docker Compose.

## Requirements 📦

- Docker
- Docker Compose
- A Telegram bot token and chat ID if you want notifications

## Installation With Docker 🚀

Create a `docker-compose.yml` file:

```yaml
services:
  dockerwatcher:
    image: greg222777/docker-watcher:latest
    container_name: dockerwatcher
    restart: unless-stopped
    environment:
      - TELEGRAM_BOT_TOKEN=your_bot_token_here
      - TELEGRAM_CHAT_ID=your_chat_id_here
      - WEB_PORT=8000
      - DATA_DIR=/data
      - LOG_LEVEL=INFO
    ports:
      - "8000:8000"
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
      - ./data:/data
```

Then start Docker Watcher:

```sh
docker compose up -d
```

Open the web UI:

```text
http://localhost:8000
```

## Configuration ⚙️

| Variable | Default | Description |
| --- | --- | --- |
| `TELEGRAM_BOT_TOKEN` | empty | Telegram bot token. Leave empty to disable notifications. |
| `TELEGRAM_CHAT_ID` | empty | Telegram chat ID that should receive notifications. |
| `WEB_PORT` | `8000` | Port used by the Flask web UI inside the container. |
| `DATA_DIR` | `/data` | Internal directory used for the SQLite database and captured logs. |
| `LOG_LEVEL` | `INFO` | Application log level, for example `DEBUG`, `INFO`, `WARNING`, or `ERROR`. |

Telegram is optional. If `TELEGRAM_BOT_TOKEN` or `TELEGRAM_CHAT_ID` is missing,
Docker Watcher still runs, but notifications are skipped.

## Storage 💾

Docker Watcher stores the SQLite database and captured container logs in the
configured `DATA_DIR`.

With the Docker Compose example above, `/data` is mounted to `./data` on the
host machine:

```yaml
volumes:
  - ./data:/data
```

## Monitoring Options 👀

Docker Watcher listens to Docker container events and only records or sends
notifications for the actions selected in the web UI options.

The selection is stored in SQLite, so it is preserved when Docker Watcher
restarts.

By default, Docker Watcher monitors abnormal or operationally important
container actions:

```text
destroy
die
exec_die
health_status
kill
oom
pause
restart
stop
```

Use the official Docker event documentation to decide what matters for your
setup:

```text
https://docs.docker.com/reference/cli/docker/system/events/
```

Recommended choices:

- Keep `die`, `oom`, `kill`, `stop`, and `restart` enabled if you want alerts when containers stop, crash, or are killed.
- Keep `health_status` enabled if your containers define Docker health checks.
- Enable `start`, `create`, or `destroy` if you want lifecycle visibility, not only failures.
- Disable noisy actions such as `attach`, `resize`, `top`, or `exec_start` unless you specifically need audit-style visibility.

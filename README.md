# 🐳 Docker Watcher

Docker Watcher monitors Docker container events, stores them locally in SQLite, and can send Telegram notifications when events happen.

## ✨ Features

- 📦 Watches Docker container events
- 💾 Stores event history locally
- 📣 Sends Telegram notifications
- 🌐 Provides a lightweight web UI
- 🐋 Runs with Docker Compose

## 📋 Requirements

- Docker
- Docker Compose
- A Telegram bot token and chat ID if you want notifications

## 🚀 Installation With Docker

Clone the project:

```bash
git clone <repository-url>
cd docker-watcher
```

Create or update `docker-compose.yml`:

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
    ports:
      - "8000:8000"
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
      - ./data:/data
```

Replace:

- `your_bot_token_here` with your Telegram bot token
- `your_chat_id_here` with the Telegram chat ID that should receive notifications

Start Docker Watcher:

```bash
docker compose up
```

Open the web UI:

```text
http://localhost:8000
```

The SQLite database and captured container logs are stored locally in:

```text
./data
```

Telegram is optional. If the token or chat ID is missing, Docker Watcher will still run, but notifications will not be sent.

## Monitoring options

Docker Watcher listens to Docker container events and only records/sends notifications for the actions selected in the web UI.

Open the web UI, then click:

```text
Options
```

Select the Docker event actions you want to monitor, then click:

```text
Save
```

The selection is stored in SQLite, so it is preserved when Docker Watcher restarts.

By default, Docker Watcher monitors abnormal or operationally important container actions:

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

Use the official Docker event documentation to decide what matters for your setup:

```text
https://docs.docker.com/reference/cli/docker/system/events/
```

Recommended choices:

- Keep `die`, `oom`, `kill`, `stop`, and `restart` enabled if you want alerts when containers stop, crash, or are killed.
- Keep `health_status` enabled if your containers define Docker health checks.
- Enable `start`, `create`, or `destroy` if you want lifecycle visibility, not only failures.
- Disable noisy actions such as `attach`, `resize`, `top`, or `exec_start` unless you specifically need audit-style visibility.

## 📌 Project Status

This project is still in development.

Planned improvements:

- better event filtering
- richer Telegram messages
- automated tests
- production usage documentation

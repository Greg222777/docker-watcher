# 🐳 Docker Watcher

Docker Watcher monitors Docker container events, stores them locally in SQLite, and can send Telegram notifications when events happen.

## ✨ Features

- 📦 Watches Docker container events
- 💾 Stores event history locally
- 📣 Sends Telegram notifications
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
    build: .
    container_name: dockerwatcher
    restart: unless-stopped
    environment:
      - TELEGRAM_BOT_TOKEN=your_bot_token_here
      - TELEGRAM_CHAT_ID=your_chat_id_here
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
      - ./data:/data
```

Replace:

- `your_bot_token_here` with your Telegram bot token
- `your_chat_id_here` with the Telegram chat ID that should receive notifications

Start Docker Watcher:

```bash
docker compose up --build
```

The SQLite database and captured container logs are stored locally in:

```text
./data
```

Telegram is optional. If the token or chat ID is missing, Docker Watcher will still run, but notifications will not be sent.

## 📌 Project Status

This project is still in development.

Planned improvements:

- better event filtering
- richer Telegram messages
- automated tests
- production usage documentation

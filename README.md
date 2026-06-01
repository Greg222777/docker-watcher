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

## ⚙️ Telegram Setup

Create a Telegram bot with BotFather and copy the bot token.

Then get the chat ID where notifications should be sent.

Add both values in `docker-compose.yml`:

```yaml
services:
  dockerlistener:
    environment:
      - TELEGRAM_BOT_TOKEN=your_bot_token_here
      - TELEGRAM_CHAT_ID=your_chat_id_here
```

If these values are missing or invalid, Docker Watcher will still run, but Telegram notifications will not be sent.

## 🚀 Installation With Docker

Clone the project:

```bash
git clone <repository-url>
cd docker-watcher
```

Make sure `docker-compose.yml` contains your Telegram configuration:

```yaml
environment:
  - TELEGRAM_BOT_TOKEN=your_bot_token_here
  - TELEGRAM_CHAT_ID=your_chat_id_here
```

Start the service:

```bash
docker compose up --build
```

Docker Watcher will use the Docker socket from the host:

```yaml
volumes:
  - /var/run/docker.sock:/var/run/docker.sock
  - ./data:/data
```

The SQLite database is stored in:

```text
./data
```

## 📌 Project Status

This project is still in development.

Planned improvements:

- better event filtering
- richer Telegram messages
- automated tests
- production usage documentation

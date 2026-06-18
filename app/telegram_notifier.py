import logging
import os
from html import escape

import requests
from requests import RequestException

from app.models.event_log import EventLog

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
TELEGRAM_API_BASE_URL = "https://api.telegram.org"
logger = logging.getLogger(__name__)


def send_message(message: str) -> None:
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        logger.info("Telegram is not configured.")
        return

    url = f"{TELEGRAM_API_BASE_URL}/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "HTML"}

    try:
        response = requests.post(url, data=payload, timeout=10)
        response.raise_for_status()
    except RequestException as error:
        logger.warning("Could not send Telegram message: %s", error)


def send_event_log(event: EventLog) -> None:
    send_message(_event_message(event))


def _event_message(event: EventLog) -> str:
    lines = [
        "Docker event",
        f"<b>Container:</b> {escape(event.container_name)}",
        f"<b>ID:</b> <code>{escape(event.container_id)}</code>",
        f"<b>Action:</b> {escape(event.action)}",
        f"<b>Date:</b> {escape(event.created_at)}",
    ]

    if event.exit_code is not None:
        lines.append(f"<b>Exit code:</b> {escape(event.exit_code)}")

    if event.log_file_path:
        lines.append(f"<b>Logs:</b> <code>{escape(event.log_file_path)}</code>")

    return "\n".join(lines)

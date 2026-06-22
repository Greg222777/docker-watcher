import logging
import os
from datetime import datetime, timedelta
from html import escape

import requests
from requests import RequestException

from app.daily_status_analyzer import analyze_daily_status
from app.database import event_log_repository, telegram_options_repository
from app.models.event_log import EventLog
from app.openai_client import OpenAIClientError

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
TELEGRAM_API_BASE_URL = "https://api.telegram.org"
logger = logging.getLogger(__name__)


def is_configured() -> bool:
    return bool(TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID)


def send_event_notification(event: EventLog) -> None:
    if telegram_options_repository.select().receive_event_notifications:
        _send_message(_event_message(event))


def send_daily_status() -> None:
    options = telegram_options_repository.select()
    if not options.receive_daily_status or not options.daily_status_time:
        return

    now = datetime.now()
    start = now - timedelta(days=1)

    try:
        _send_message(
            analyze_daily_status(
                event_log_repository.select_between(
                    start.isoformat(timespec="seconds"),
                    now.isoformat(timespec="seconds"),
                )
            )
        )
    except OpenAIClientError as error:
        logger.warning("Could not analyze Telegram daily status: %s", error)


def _send_message(message: str) -> None:
    if not is_configured():
        logger.info("Telegram is not configured.")
        return

    url = f"{TELEGRAM_API_BASE_URL}/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "HTML"}

    try:
        response = requests.post(url, data=payload, timeout=10)
        response.raise_for_status()
    except RequestException as error:
        logger.warning("Could not send Telegram message: %s", error)


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

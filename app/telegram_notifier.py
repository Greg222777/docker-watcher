import logging
import os

import requests
from requests import RequestException

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

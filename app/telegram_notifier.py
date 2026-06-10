import logging
import os

import requests
from requests import RequestException

from app.models import EventLog

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
TELEGRAM_API_BASE_URL = "https://api.telegram.org"
logger = logging.getLogger(__name__)


class TelegramNotifier:
    def __init__(
        self,
        bot_token: str | None = TELEGRAM_BOT_TOKEN,
        chat_id: str | None = TELEGRAM_CHAT_ID,
    ) -> None:
        self.bot_token = bot_token
        self.chat_id = chat_id

    def send_message(self, message: str) -> None:
        """
        Send a message to a Telegram chat.
        """
        if not self.bot_token or not self.chat_id:
            logger.info("Telegram is not configured.")
            return

        url = f"{TELEGRAM_API_BASE_URL}/bot{self.bot_token}/sendMessage"

        payload = {"chat_id": self.chat_id, "text": message, "parse_mode": "HTML"}

        try:
            response = requests.post(url, data=payload, timeout=10)
            response.raise_for_status()
        except RequestException as error:
            logger.warning("Could not send Telegram message: %s", error)

    def send_event_log(self, event: EventLog) -> None:
        """
        Send a Docker event log to a Telegram chat.
        """
        self.send_message(event.to_telegram_message())


telegram_notifier = TelegramNotifier()

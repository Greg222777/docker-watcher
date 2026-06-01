import os
from typing import Optional

import requests

from app.models import EventLog


TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")


class TelegramNotifier:
    def __init__(
        self,
        bot_token: Optional[str] = TELEGRAM_BOT_TOKEN,
        chat_id: Optional[str] = TELEGRAM_CHAT_ID
    ) -> None:
        self.bot_token = bot_token
        self.chat_id = chat_id

    def send_message(self, message: str) -> None:
        """
        Send a message to a Telegram chat.
        """
        if not self.bot_token or not self.chat_id:
            print("Telegram is not configured.")
            return

        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"

        payload = {
            "chat_id": self.chat_id,
            "text": message,
            "parse_mode": "HTML"
        }

        try:
            response = requests.post(url, data=payload, timeout=10)
            response.raise_for_status()
        except requests.RequestException as e:
            print(f"Could not send Telegram message: {e}")

    def send_event_log(self, event: EventLog) -> None:
        """
        Send a Docker event log to a Telegram chat.
        """
        self.send_message(event.to_telegram_message())


telegram_notifier = TelegramNotifier()


def send_telegram_message(message: str) -> None:
    telegram_notifier.send_message(message)


def send_event_log(event: EventLog) -> None:
    telegram_notifier.send_event_log(event)

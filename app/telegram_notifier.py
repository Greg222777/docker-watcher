import os
from typing import Optional
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

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

        payload = urlencode({
            "chat_id": self.chat_id,
            "text": message,
            "parse_mode": "HTML"
        }).encode("utf-8")

        request = Request(url=url, data=payload, method="POST")

        try:
            with urlopen(request, timeout=10) as response:
                response.read()
        except HTTPError as error:
            print(f"Could not send Telegram message: HTTP {error.code}")
        except URLError as error:
            print(f"Could not send Telegram message: {error.reason}")

    def send_event_log(self, event: EventLog) -> None:
        """
        Send a Docker event log to a Telegram chat.
        """
        self.send_message(event.to_telegram_message())


telegram_notifier = TelegramNotifier()

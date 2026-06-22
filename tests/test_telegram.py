from datetime import datetime
from unittest.mock import Mock, patch

import pytest

from app import telegram
from app.models.event_log import EventLog
from app.models.telegram_options import TelegramOptions


@pytest.mark.parametrize(
    ("enabled", "expected_calls"),
    [
        (False, 0),
        (True, 1),
    ],
)
def test_send_event_notification_respects_option(
    enabled: bool,
    expected_calls: int,
) -> None:
    with (
        patch(
            "app.telegram.telegram_options_repository.select",
            return_value=TelegramOptions(receive_event_notifications=enabled),
        ),
        patch("app.telegram._send_message") as send_message,
    ):
        telegram.send_event_notification(
            EventLog(container_name="api", container_id="abcdef", action="die")
        )

    assert send_message.call_count == expected_calls


def test_send_daily_status_sends_current_status() -> None:
    events_repository = Mock()
    events_repository.count_filtered.return_value = 3

    with (
        patch(
            "app.telegram.telegram_options_repository.select",
            return_value=TelegramOptions(
                receive_daily_status=True,
                daily_status_time="07:30",
            ),
        ),
        patch("app.telegram._send_message") as send_message,
        patch("app.telegram.event_log_repository", events_repository),
        patch("app.telegram.datetime") as datetime_mock,
    ):
        datetime_mock.now.return_value = datetime(2026, 6, 22, 7, 30)
        telegram.send_daily_status()

    send_message.assert_called_once()
    assert "Docker Watcher daily status" in send_message.call_args.args[0]
    assert "<b>Events recorded:</b> 3" in send_message.call_args.args[0]

from datetime import datetime
from unittest.mock import Mock, patch

import pytest

from app import telegram_client
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
            "app.telegram_client.telegram_options_repository.select",
            return_value=TelegramOptions(receive_event_notifications=enabled),
        ),
        patch("app.telegram_client._send_message") as send_message,
    ):
        telegram_client.send_event_notification(
            EventLog(container_name="api", container_id="abcdef", action="die")
        )

    assert send_message.call_count == expected_calls


def test_send_daily_status_sends_current_status() -> None:
    event = EventLog(container_name="api", container_id="abcdef", action="restart")
    events_repository = Mock()
    events_repository.select_between.return_value = [event]

    with (
        patch(
            "app.telegram_client.telegram_options_repository.select",
            return_value=TelegramOptions(
                receive_daily_status=True,
                daily_status_time="07:30",
            ),
        ),
        patch("app.telegram_client._send_message") as send_message,
        patch(
            "app.telegram_client.analyze_daily_status",
            return_value="Daily status\n✅ Nothing to report.",
        ) as analyze_daily_status,
        patch("app.telegram_client.event_log_repository", events_repository),
        patch("app.telegram_client.datetime") as datetime_mock,
    ):
        datetime_mock.now.return_value = datetime(2026, 6, 22, 7, 30)
        telegram_client.send_daily_status()

    analyze_daily_status.assert_called_once_with([event])
    send_message.assert_called_once()
    assert "Daily status" in send_message.call_args.args[0]
    assert "Nothing to report" in send_message.call_args.args[0]

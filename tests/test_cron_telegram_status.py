from unittest.mock import patch

from apscheduler.triggers.cron import CronTrigger

from app import cron_telegram_status
from app.models.telegram_options import TelegramOptions


def test_sync_schedule_adds_daily_status_job() -> None:
    with (
        patch("app.cron_telegram_status.is_configured", return_value=True),
        patch(
            "app.cron_telegram_status.telegram_options_repository.select",
            return_value=TelegramOptions(
                receive_daily_status=True,
                daily_status_time="07:30",
            ),
        ),
        patch("app.cron_telegram_status.scheduler") as scheduler,
    ):
        scheduler.running = False
        cron_telegram_status.sync_schedule()

    scheduler.start.assert_called_once()
    scheduler.add_job.assert_called_once()
    assert scheduler.add_job.call_args.args[0] is cron_telegram_status.send_daily_status
    assert scheduler.add_job.call_args.kwargs["id"] == "telegram_daily_status"
    assert scheduler.add_job.call_args.kwargs["replace_existing"] is True
    assert isinstance(scheduler.add_job.call_args.args[1], CronTrigger)


def test_sync_schedule_removes_job_without_required_options() -> None:
    job = object()

    for options in [
        TelegramOptions(receive_daily_status=False, daily_status_time="07:30"),
        TelegramOptions(receive_daily_status=True, daily_status_time=""),
    ]:
        with (
            patch("app.cron_telegram_status.is_configured", return_value=True),
            patch(
                "app.cron_telegram_status.telegram_options_repository.select",
                return_value=options,
            ),
            patch("app.cron_telegram_status.scheduler") as scheduler,
        ):
            scheduler.get_job.return_value = job
            cron_telegram_status.sync_schedule()

        scheduler.remove_job.assert_called_once_with("telegram_daily_status")
        scheduler.add_job.assert_not_called()


def test_sync_schedule_does_not_start_scheduler_when_telegram_is_not_configured() -> None:
    with (
        patch("app.cron_telegram_status.is_configured", return_value=False),
        patch("app.cron_telegram_status.scheduler") as scheduler,
    ):
        cron_telegram_status.sync_schedule()

    scheduler.start.assert_not_called()

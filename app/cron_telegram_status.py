import logging
from datetime import time

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.database import telegram_options_repository
from app.telegram import is_configured, send_daily_status

DAILY_STATUS_JOB_ID = "telegram_daily_status"
logger = logging.getLogger(__name__)
scheduler = BackgroundScheduler()


def start() -> None:
    if not is_configured():
        logger.info("Telegram daily status cron is disabled: Telegram is not configured.")
        return

    if not scheduler.running:
        scheduler.start()

    sync_schedule()


def sync_schedule() -> None:
    if not is_configured():
        _remove_job()
        return

    scheduled_time = _scheduled_time()
    if scheduled_time is None:
        _remove_job()
        return

    scheduler.add_job(
        send_daily_status,
        CronTrigger(hour=scheduled_time.hour, minute=scheduled_time.minute),
        id=DAILY_STATUS_JOB_ID,
        replace_existing=True,
    )
    logger.info("Telegram daily status cron scheduled at %s.", scheduled_time)


def _remove_job() -> None:
    if scheduler.get_job(DAILY_STATUS_JOB_ID):
        scheduler.remove_job(DAILY_STATUS_JOB_ID)


def _scheduled_time() -> time | None:
    options = telegram_options_repository.select()

    if not options.receive_daily_status or not options.daily_status_time:
        return None

    try:
        return time.fromisoformat(options.daily_status_time)
    except ValueError:
        return None

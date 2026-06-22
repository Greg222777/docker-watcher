from app.database.schema import init_schema
from app.database.telegram_options import TelegramOptionsRepository
from app.models.telegram_options import TelegramOptions


def test_select_returns_default_telegram_options(tmp_path) -> None:
    db_path = tmp_path / "docker_events.db"
    repository = TelegramOptionsRepository(str(db_path))
    init_schema(db_path)

    assert repository.select() == TelegramOptions()


def test_save_persists_telegram_options(tmp_path) -> None:
    db_path = tmp_path / "docker_events.db"
    repository = TelegramOptionsRepository(str(db_path))
    init_schema(db_path)
    options = TelegramOptions(
        receive_daily_status=True,
        daily_status_time="07:30",
        receive_event_notifications=False,
    )

    repository.save(options)

    assert repository.select() == options

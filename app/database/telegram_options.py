from app.config import DB_PATH
from app.database.session import create_session_factory
from app.database.tables import TelegramOptionsRecord
from app.models.telegram_options import TelegramOptions

TELEGRAM_OPTIONS_ID = 1


class TelegramOptionsRepository:
    def __init__(self, db_path: str | None = None) -> None:
        self.db_path = str(db_path or DB_PATH)
        self.session_factory = create_session_factory(self.db_path)

    def select(self) -> TelegramOptions:
        with self.session_factory() as session:
            record = session.get(TelegramOptionsRecord, TELEGRAM_OPTIONS_ID)

            if not record:
                return TelegramOptions()

            return TelegramOptions(
                receive_daily_status=record.receive_daily_status,
                daily_status_time=record.daily_status_time,
                receive_event_notifications=record.receive_event_notifications,
            )

    def save(self, options: TelegramOptions) -> None:
        with self.session_factory.begin() as session:
            session.merge(
                TelegramOptionsRecord(
                    id=TELEGRAM_OPTIONS_ID,
                    receive_daily_status=options.receive_daily_status,
                    daily_status_time=options.daily_status_time,
                    receive_event_notifications=options.receive_event_notifications,
                )
            )

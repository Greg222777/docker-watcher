from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.session import Base
from app.models import EventLog


class ContainerEventRecord(Base):
    __tablename__ = "container_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    container_name: Mapped[str] = mapped_column(Text, nullable=False)
    container_id: Mapped[str] = mapped_column(Text, nullable=False)
    action: Mapped[str] = mapped_column(Text, nullable=False)
    exit_code: Mapped[str | None] = mapped_column(Text)
    log_file_path: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[str] = mapped_column(Text, nullable=False)

    @classmethod
    def from_event_log(cls, event: EventLog) -> "ContainerEventRecord":
        return cls(
            container_name=event.container_name,
            container_id=event.container_id,
            action=event.action,
            exit_code=event.exit_code,
            log_file_path=event.log_file_path,
            created_at=event.created_at,
        )

    def to_event_log(self) -> EventLog:
        return EventLog(
            id=self.id,
            container_name=self.container_name,
            container_id=self.container_id,
            action=self.action,
            exit_code=self.exit_code,
            log_file_path=self.log_file_path,
            created_at=self.created_at,
        )


class MonitoredEventActionRecord(Base):
    __tablename__ = "monitored_event_actions"

    action: Mapped[str] = mapped_column(String, primary_key=True)

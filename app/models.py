from dataclasses import dataclass, field
from datetime import datetime
from html import escape
from typing import Any, Optional


@dataclass
class EventLog:
    container_name: str
    container_id: str
    action: str
    exit_code: Optional[str] = None
    log_file_path: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    id: Optional[int] = None

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> "EventLog":
        return cls(
            id=row.get("id"),
            container_name=row["container_name"],
            container_id=row["container_id"],
            action=row["action"],
            exit_code=row.get("exit_code"),
            log_file_path=row.get("log_file_path"),
            created_at=row["created_at"],
        )

    def to_insert_values(self) -> tuple[str, str, str, Optional[str], Optional[str], str]:
        return (
            self.container_name,
            self.container_id,
            self.action,
            self.exit_code,
            self.log_file_path,
            self.created_at,
        )

    def to_telegram_message(self) -> str:
        lines = [
            "<b>Docker event</b>",
            f"<b>Container:</b> {escape(self.container_name)}",
            f"<b>ID:</b> <code>{escape(self.container_id[:12])}</code>",
            f"<b>Action:</b> {escape(self.action)}",
            f"<b>Date:</b> {escape(self.created_at)}",
        ]

        if self.exit_code is not None:
            lines.append(f"<b>Exit code:</b> {escape(self.exit_code)}")

        if self.log_file_path:
            lines.append(f"<b>Logs:</b> <code>{escape(self.log_file_path)}</code>")

        return "\n".join(lines)

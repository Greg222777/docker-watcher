from dataclasses import dataclass, field
from datetime import datetime
from html import escape


@dataclass
class EventLog:
    container_name: str
    container_id: str
    action: str
    exit_code: str | None = None
    log_file_path: str | None = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    id: int | None = None

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

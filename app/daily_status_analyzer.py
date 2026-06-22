from pathlib import Path

from app.models.event_log import EventLog
from app.openai_client import OPENAI_MODEL, send_prompt

PROMPT_TEMPLATE_PATH = (
    Path(__file__).resolve().parent / "prompts" / "daily_status_prompt.txt"
)


def analyze_daily_status(
    events: list[EventLog],
    api_key: str | None = None,
    model: str = OPENAI_MODEL,
) -> str:
    return send_prompt(prompt=_build_prompt(events), api_key=api_key, model=model)


def _build_prompt(events: list[EventLog]) -> str:
    return PROMPT_TEMPLATE_PATH.read_text(encoding="utf-8").format(
        events=_events_text(events)
    )


def _events_text(events: list[EventLog]) -> str:
    if not events:
        return "No events recorded."

    lines = [
        (
            f"- {event.created_at} | {event.container_name} | "
            f"{event.container_id[:12]} | {event.action} | "
            f"exit={event.exit_code or 'unknown'}"
        )
        for event in events
    ]
    return "\n".join(lines)

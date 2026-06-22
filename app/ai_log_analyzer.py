from pathlib import Path

from app.models.event_log import EventLog
from app.openai_client import OPENAI_MODEL, OpenAIClientError, send_prompt

MAX_LOG_CHARS = 20000
PROMPT_TEMPLATE_PATH = (
    Path(__file__).resolve().parent / "prompts" / "ai_log_analysis_prompt.txt"
)


class AILogAnalysisError(Exception):
    """Raised when an AI log analysis cannot be completed."""


def analyze_event_log(
    event: EventLog,
    log_path: Path,
    api_key: str | None = None,
    model: str = OPENAI_MODEL,
) -> str:
    log_content = _read_log_file(log_path)
    prompt = _build_prompt(event=event, log_content=log_content)

    try:
        return send_prompt(prompt=prompt, api_key=api_key, model=model)
    except OpenAIClientError as error:
        raise AILogAnalysisError(str(error)) from error


def _read_log_file(log_path: Path) -> str:
    try:
        log_content = log_path.read_text(encoding="utf-8", errors="replace")
    except OSError as error:
        raise AILogAnalysisError(f"Could not read log file: {error}") from error

    if len(log_content) <= MAX_LOG_CHARS:
        return log_content

    omitted_chars = len(log_content) - MAX_LOG_CHARS
    return (
        f"[Log truncated: {omitted_chars} characters omitted from the beginning.]\n"
        f"{log_content[-MAX_LOG_CHARS:]}"
    )


def _build_prompt(event: EventLog, log_content: str) -> str:
    return PROMPT_TEMPLATE_PATH.read_text(encoding="utf-8").format(
        event_id=event.id or "unknown",
        container_name=event.container_name,
        container_id=event.container_id,
        action=event.action,
        exit_code=event.exit_code if event.exit_code is not None else "unknown",
        created_at=event.created_at,
        log_file_path=event.log_file_path or "unknown",
        log_content=log_content,
    )

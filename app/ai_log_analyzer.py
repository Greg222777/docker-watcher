import os
from pathlib import Path
from typing import Any

import requests
from requests import RequestException

from app.models import EventLog

OPENAI_RESPONSES_URL = "https://api.openai.com/v1/responses"
OPENAI_MODEL = "gpt-4o-mini"
MAX_LOG_CHARS = 20000
PROMPT_TEMPLATE_PATH = Path(__file__).resolve().parent / "prompts" / "ai_log_analysis_prompt.txt"


class AILogAnalysisError(Exception):
    """Raised when an AI log analysis cannot be completed."""


class OpenAILogAnalyzer:
    def __init__(
        self,
        api_key: str | None = None,
        model: str = OPENAI_MODEL,
    ) -> None:
        self.api_key = os.getenv("OPENAI_API_KEY") if api_key is None else api_key
        self.model = model

    def analyze_event_log(self, event: EventLog, log_path: Path) -> str:
        log_content = self._read_log_file(log_path)
        prompt = self._build_prompt(event=event, log_content=log_content)

        return self._send_prompt(prompt)

    def _read_log_file(self, log_path: Path) -> str:
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

    def _build_prompt(self, event: EventLog, log_content: str) -> str:
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

    def _send_prompt(self, prompt: str) -> str:
        if not self.api_key:
            raise AILogAnalysisError("OPENAI_API_KEY is not set.")

        payload: dict[str, Any] = {
            "model": self.model,
            "input": prompt,
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        try:
            session = requests.Session()
            session.trust_env = False
            response = session.post(
                OPENAI_RESPONSES_URL,
                json=payload,
                headers=headers,
                timeout=45,
            )
            response.raise_for_status()
        except RequestException as error:
            raise AILogAnalysisError(f"OpenAI request failed: {error}") from error

        data = response.json()
        output_text = data.get("output_text")

        if isinstance(output_text, str) and output_text.strip():
            return output_text.strip()

        extracted_text = self._extract_text_from_response(data)
        if extracted_text:
            return extracted_text

        raise AILogAnalysisError("OpenAI response did not contain analysis text.")

    def _extract_text_from_response(self, data: dict[str, Any]) -> str:
        text_parts: list[str] = []

        for output_item in data.get("output", []):
            for content_item in output_item.get("content", []):
                text = content_item.get("text")
                if isinstance(text, str) and text.strip():
                    text_parts.append(text.strip())

        return "\n\n".join(text_parts)

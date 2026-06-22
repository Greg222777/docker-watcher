import os
from typing import Any

import requests
from requests import RequestException

OPENAI_RESPONSES_URL = "https://api.openai.com/v1/responses"
OPENAI_MODEL = "gpt-4o-mini"


class OpenAIClientError(Exception):
    """Raised when an OpenAI request cannot be completed."""


def send_prompt(
    prompt: str,
    api_key: str | None = None,
    model: str = OPENAI_MODEL,
) -> str:
    resolved_api_key = os.getenv("OPENAI_API_KEY") if api_key is None else api_key

    if not resolved_api_key:
        raise OpenAIClientError("OPENAI_API_KEY is not set.")

    payload: dict[str, Any] = {
        "model": model,
        "input": prompt,
    }
    headers = {
        "Authorization": f"Bearer {resolved_api_key}",
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
        raise OpenAIClientError(f"OpenAI request failed: {error}") from error

    data = response.json()
    output_text = data.get("output_text")

    if isinstance(output_text, str) and output_text.strip():
        return output_text.strip()

    extracted_text = _extract_text_from_response(data)
    if extracted_text:
        return extracted_text

    raise OpenAIClientError("OpenAI response did not contain analysis text.")


def _extract_text_from_response(data: dict[str, Any]) -> str:
    text_parts: list[str] = []

    for output_item in data.get("output", []):
        for content_item in output_item.get("content", []):
            text = content_item.get("text")
            if isinstance(text, str) and text.strip():
                text_parts.append(text.strip())

    return "\n\n".join(text_parts)

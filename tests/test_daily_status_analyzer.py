from unittest.mock import patch

from app.daily_status_analyzer import (
    _build_prompt,
    analyze_daily_status,
)
from app.models.event_log import EventLog


def test_build_prompt_includes_events_and_daily_status_rules() -> None:
    prompt = _build_prompt(
        [
            EventLog(
                container_name="api",
                container_id="abcdef1234567890",
                action="kill",
                exit_code="137",
                created_at="2026-06-22T07:00:00",
            ),
            EventLog(
                container_name="api",
                container_id="abcdef1234567890",
                action="restart",
                created_at="2026-06-22T07:01:00",
            ),
        ]
    )

    assert "Daily status" in prompt
    assert "api" in prompt
    assert "kill" in prompt
    assert "restart" in prompt
    assert "probable update/maintenance" in prompt


def test_analyze_daily_status_uses_common_openai_client() -> None:
    with patch(
        "app.daily_status_analyzer.send_prompt",
        return_value="Daily status\n✅ Nothing to report.",
    ) as send_prompt:
        analysis = analyze_daily_status([], api_key="test-key", model="test-model")

    assert analysis == "Daily status\n✅ Nothing to report."
    send_prompt.assert_called_once()
    assert send_prompt.call_args.kwargs["api_key"] == "test-key"
    assert send_prompt.call_args.kwargs["model"] == "test-model"

from unittest.mock import Mock, patch

import pytest

from app.ai_log_analyzer import MAX_LOG_CHARS, AILogAnalysisError, OpenAILogAnalyzer
from app.models import EventLog


def build_event() -> EventLog:
    return EventLog(
        id=42,
        container_name="worker-storage",
        container_id="b8d7a4f1c9e24001a88bb66123cc9900",
        action="die",
        exit_code="1",
        log_file_path="/data/logs/worker-storage.log",
        created_at="2026-06-10T14:23:16",
    )


def test_build_prompt_includes_context_event_metadata_and_log() -> None:
    analyzer = OpenAILogAnalyzer(api_key="test-key")

    prompt = analyzer._build_prompt(
        event=build_event(),
        log_content="FATAL persistent storage unavailable",
    )

    assert "Docker Watcher is a small monitoring application" in prompt
    assert "worker-storage" in prompt
    assert "b8d7a4f1c9e24001a88bb66123cc9900" in prompt
    assert "Docker action: die" in prompt
    assert "Exit code: 1" in prompt
    assert "FATAL persistent storage unavailable" in prompt
    assert "Recommended fix" in prompt


def test_analyze_event_log_sends_prompt_to_openai(test_log_dir) -> None:
    log_path = test_log_dir / "event.log"
    log_path.write_text("SQLITE_FULL: database or disk is full", encoding="utf-8")
    response = Mock()
    response.json.return_value = {"output_text": "Disk is full. Free space."}
    response.raise_for_status.return_value = None

    with patch(
        "app.ai_log_analyzer.requests.Session.post", return_value=response
    ) as post:
        analysis = OpenAILogAnalyzer(
            api_key="test-key",
            model="test-model",
        ).analyze_event_log(
            event=build_event(),
            log_path=log_path,
        )

    assert analysis == "Disk is full. Free space."
    post.assert_called_once()
    request_kwargs = post.call_args.kwargs
    assert request_kwargs["json"]["model"] == "test-model"
    assert "SQLITE_FULL" in request_kwargs["json"]["input"]
    assert request_kwargs["headers"]["Authorization"] == "Bearer test-key"


def test_analyze_event_log_requires_api_key(test_log_dir) -> None:
    log_path = test_log_dir / "event.log"
    log_path.write_text("container logs", encoding="utf-8")

    with pytest.raises(AILogAnalysisError, match="OPENAI_API_KEY is not set"):
        OpenAILogAnalyzer(api_key="").analyze_event_log(
            event=build_event(),
            log_path=log_path,
        )


def test_read_log_file_truncates_from_the_beginning(test_log_dir) -> None:
    log_path = test_log_dir / "event.log"
    log_path.write_text(f"start-{'x' * MAX_LOG_CHARS}", encoding="utf-8")

    log_content = OpenAILogAnalyzer(api_key="test-key")._read_log_file(log_path)

    assert "6 characters omitted" in log_content
    assert log_content.endswith("x" * MAX_LOG_CHARS)

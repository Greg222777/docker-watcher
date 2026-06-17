from unittest.mock import patch

import pytest

from app import web_server
from app.models.docker_event_action import DockerEventAction
from app.models.event_log import EventLog


@pytest.fixture
def web_client():
    web_server.app.config.update(TESTING=True)
    return web_server.app.test_client()


def test_events_page_renders_events(web_client) -> None:
    event = EventLog(
        id=1,
        container_name="api",
        container_id="abcdef1234567890",
        action="die",
        created_at="2026-06-02T10:00:00",
    )

    with (
        patch.object(
            web_server.event_log_repository,
            "count_filtered",
            return_value=1,
        ),
        patch.object(
            web_server.event_log_repository,
            "select_filtered",
            return_value=[event],
        ) as select_filtered,
        patch.object(
            web_server.monitored_event_action_repository,
            "select_all",
        ) as select_monitored_actions,
    ):
        select_monitored_actions.return_value = {DockerEventAction.DIE}

        response = web_client.get("/")

    assert response.status_code == 200
    assert b"Docker Watcher" in response.data
    assert b"/static/css/events.css" in response.data
    assert b"Delete all recorded events and log files?" in response.data
    assert b"api" in response.data
    assert b"abcdef123456" in response.data
    select_filtered.assert_called_once_with(
        start_timestamp="",
        end_timestamp="",
        container_filter="",
        action_filter="",
        limit=web_server.EVENTS_PER_PAGE,
        offset=0,
    )


def test_events_page_renders_ai_analysis_button_for_events_with_logs(
    web_client,
) -> None:
    event = EventLog(
        id=1,
        container_name="api",
        container_id="abcdef1234567890",
        action="die",
        log_file_path="/data/logs/event.log",
    )

    with (
        patch.object(
            web_server.event_log_repository,
            "count_filtered",
            return_value=1,
        ),
        patch.object(
            web_server.event_log_repository,
            "select_filtered",
            return_value=[event],
        ),
        patch.object(
            web_server.monitored_event_action_repository,
            "select_all",
            return_value={DockerEventAction.DIE},
        ),
    ):
        response = web_client.get("/")

    assert response.status_code == 200
    assert b"AI" in response.data
    assert b"Analyze this log file with AI" in response.data
    assert b"/events/1/ai-analysis" in response.data


def test_events_page_filters_by_event_action(web_client) -> None:
    event = EventLog(
        id=1,
        container_name="api",
        container_id="abcdef1234567890",
        action="die",
    )

    with (
        patch.object(
            web_server.event_log_repository,
            "count_filtered",
            return_value=1,
        ),
        patch.object(
            web_server.event_log_repository,
            "select_filtered",
            return_value=[event],
        ) as select_filtered,
        patch.object(
            web_server.monitored_event_action_repository,
            "select_all",
        ) as select_monitored_actions,
    ):
        select_monitored_actions.return_value = {DockerEventAction.DIE}

        response = web_client.get("/?event=die")

    assert response.status_code == 200
    assert b"api" in response.data
    assert b"worker" not in response.data
    select_filtered.assert_called_once_with(
        start_timestamp="",
        end_timestamp="",
        container_filter="",
        action_filter="die",
        limit=web_server.EVENTS_PER_PAGE,
        offset=0,
    )


def test_events_page_paginates_and_preserves_filters(web_client) -> None:
    event = EventLog(
        id=51,
        container_name="api",
        container_id="abcdef1234567890",
        action="die",
    )

    with (
        patch.object(
            web_server.event_log_repository,
            "count_filtered",
            return_value=75,
        ),
        patch.object(
            web_server.event_log_repository,
            "select_filtered",
            return_value=[event],
        ) as select_filtered,
        patch.object(
            web_server.monitored_event_action_repository,
            "select_all",
            return_value={DockerEventAction.DIE},
        ),
    ):
        response = web_client.get("/?container=api&event=die&page=2")

    assert response.status_code == 200
    total_pages = (75 + web_server.EVENTS_PER_PAGE - 1) // web_server.EVENTS_PER_PAGE
    assert f"Page 2 of {total_pages}".encode() in response.data
    assert b"Previous" in response.data
    assert b"container=api" in response.data
    assert b"event=die" in response.data
    select_filtered.assert_called_once_with(
        start_timestamp="",
        end_timestamp="",
        container_filter="api",
        action_filter="die",
        limit=web_server.EVENTS_PER_PAGE,
        offset=web_server.EVENTS_PER_PAGE,
    )


def test_log_file_serves_files_from_log_dir(web_client, test_log_dir) -> None:
    log_file = test_log_dir / "event.log"
    log_file.write_text("container logs", encoding="utf-8")

    with patch.object(web_server, "LOG_DIR", test_log_dir.resolve()):
        response = web_client.get("/logs/event.log")

    assert response.status_code == 200
    assert response.text == "container logs"
    response.close()


def test_ai_log_analysis_page_renders_loader(web_client, test_log_dir) -> None:
    event = EventLog(
        id=1,
        container_name="api",
        container_id="abcdef1234567890",
        action="die",
        log_file_path=str(test_log_dir / "event.log"),
    )
    log_file = test_log_dir / "event.log"
    log_file.write_text("container logs", encoding="utf-8")

    with (
        patch.object(web_server, "LOG_DIR", test_log_dir.resolve()),
        patch.object(
            web_server.event_log_repository, "select_by_id", return_value=event
        ),
    ):
        response = web_client.get("/events/1/ai-analysis")

    assert response.status_code == 200
    assert b"AI Log Analysis" in response.data
    assert b"Analyzing logs with OpenAI..." in response.data
    assert b"/events/1/ai-analysis/result" in response.data


def test_ai_log_analysis_result_requires_api_key(web_client, test_log_dir) -> None:
    event = EventLog(
        id=1,
        container_name="api",
        container_id="abcdef1234567890",
        action="die",
        log_file_path=str(test_log_dir / "event.log"),
    )
    log_file = test_log_dir / "event.log"
    log_file.write_text("container logs", encoding="utf-8")

    with (
        patch.object(web_server, "LOG_DIR", test_log_dir.resolve()),
        patch.object(
            web_server.event_log_repository, "select_by_id", return_value=event
        ),
        patch.dict("os.environ", {"OPENAI_API_KEY": ""}),
    ):
        response = web_client.get("/events/1/ai-analysis/result")

    assert response.status_code == 503
    assert response.json == {
        "error": "AI log analysis failed: OPENAI_API_KEY is not set."
    }


def test_ai_log_analysis_result_returns_analysis(web_client, test_log_dir) -> None:
    event = EventLog(
        id=1,
        container_name="api",
        container_id="abcdef1234567890",
        action="die",
        log_file_path=str(test_log_dir / "event.log"),
    )
    log_file = test_log_dir / "event.log"
    log_file.write_text("container logs", encoding="utf-8")

    with (
        patch.object(web_server, "LOG_DIR", test_log_dir.resolve()),
        patch.object(
            web_server.event_log_repository, "select_by_id", return_value=event
        ),
        patch.object(
            web_server,
            "analyze_event_log",
            return_value="Fix disk space.",
        ),
    ):
        response = web_client.get("/events/1/ai-analysis/result")

    assert response.status_code == 200
    assert response.json == {"analysis": "Fix disk space."}


def test_static_css_is_served(web_client) -> None:
    response = web_client.get("/static/css/events.css")

    assert response.status_code == 200
    assert b".toolbar" in response.data


def test_save_monitoring_options_updates_repository(web_client) -> None:
    with patch.object(
        web_server.monitored_event_action_repository,
        "replace_all",
    ) as replace_all:
        response = web_client.post(
            "/options/monitoring",
            data={
                "actions": ["die", "oom", "not-real"],
                "redirect_to": "/events?container=api",
            },
        )

    assert response.status_code == 302
    assert response.headers["Location"] == "/events?container=api"
    replace_all.assert_called_once_with(
        {
            DockerEventAction.DIE,
            DockerEventAction.OOM,
        }
    )

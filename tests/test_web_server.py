from unittest.mock import patch

import pytest

from app import web_server
from app.models import DockerEventAction, EventLog


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
    assert b"Page 2 of 38" in response.data
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
    replace_all.assert_called_once_with({
        DockerEventAction.DIE,
        DockerEventAction.OOM,
    })

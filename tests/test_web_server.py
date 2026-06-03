import unittest
from pathlib import Path
from unittest.mock import patch

from app.models import DockerEventAction, EventLog
from app import web_server


TEST_DIR = Path(__file__).resolve().parent
TEST_LOG_DIR = TEST_DIR / "logs"


class WebServerTest(unittest.TestCase):
    def setUp(self) -> None:
        web_server.app.config.update(TESTING=True)
        self.client = web_server.app.test_client()

    def tearDown(self) -> None:
        self._clear_test_logs()

    def test_events_page_renders_events(self) -> None:
        event = EventLog(
            id=1,
            container_name="api",
            container_id="abcdef1234567890",
            action="die",
            created_at="2026-06-02T10:00:00",
        )

        with (
            patch.object(web_server.event_log_repository, "select_all") as select_all,
            patch.object(
                web_server.monitored_event_action_repository,
                "select_all",
            ) as select_monitored_actions,
        ):
            select_all.return_value = [event]
            select_monitored_actions.return_value = {DockerEventAction.DIE}

            response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Docker Watcher", response.data)
        self.assertIn(b"api", response.data)
        self.assertIn(b"abcdef123456", response.data)

    def test_events_page_filters_by_event_action(self) -> None:
        events = [
            EventLog(
                id=1,
                container_name="api",
                container_id="abcdef1234567890",
                action="die",
            ),
            EventLog(
                id=2,
                container_name="worker",
                container_id="1234567890abcdef",
                action="start",
            ),
        ]

        with (
            patch.object(web_server.event_log_repository, "select_all") as select_all,
            patch.object(
                web_server.monitored_event_action_repository,
                "select_all",
            ) as select_monitored_actions,
        ):
            select_all.return_value = events
            select_monitored_actions.return_value = {DockerEventAction.DIE}

            response = self.client.get("/?event=die")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"api", response.data)
        self.assertNotIn(b"worker", response.data)

    def test_event_filter_normalizes_health_status_actions(self) -> None:
        events = [
            EventLog(
                container_name="api",
                container_id="abcdef1234567890",
                action="health_status: healthy",
            ),
            EventLog(
                container_name="worker",
                container_id="1234567890abcdef",
                action="die",
            ),
        ]

        filtered_events = web_server._filter_events(
            events=events,
            container_filter="",
            event_filter="health_status",
        )

        self.assertEqual([event.container_name for event in filtered_events], ["api"])

    def test_log_file_serves_files_from_log_dir(self) -> None:
        self._clear_test_logs()
        log_file = TEST_LOG_DIR / "event.log"
        log_file.write_text("container logs", encoding="utf-8")

        with patch.object(web_server, "LOG_DIR", TEST_LOG_DIR.resolve()):
            response = self.client.get("/logs/event.log")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.text, "container logs")
        response.close()

    def test_save_monitoring_options_updates_repository(self) -> None:
        with patch.object(
            web_server.monitored_event_action_repository,
            "replace_all",
        ) as replace_all:
            response = self.client.post(
                "/options/monitoring",
                data={
                    "actions": ["die", "oom", "not-real"],
                    "redirect_to": "/events?container=api",
                },
            )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], "/events?container=api")
        replace_all.assert_called_once_with({
            DockerEventAction.DIE,
            DockerEventAction.OOM,
        })

    def _clear_test_logs(self) -> None:
        TEST_LOG_DIR.mkdir(exist_ok=True)

        for file_path in TEST_LOG_DIR.iterdir():
            if file_path.is_file():
                file_path.unlink()


if __name__ == "__main__":
    unittest.main()

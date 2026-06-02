import os
from html import escape
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from shutil import rmtree
from threading import Thread
from urllib.parse import parse_qs, unquote, urlparse

from app.database import (
    delete_all_events,
    replace_monitored_event_actions,
    select_all_events,
    select_events_between,
    select_monitored_event_actions,
)
from app.models import CONTAINER_EVENT_ACTIONS, DockerEventAction

WEB_HOST = "0.0.0.0"
WEB_PORT = int(os.getenv("WEB_PORT", "8000"))
LOG_DIR = Path("/data/logs").resolve()


class EventLogRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        parsed_url = urlparse(self.path)

        if parsed_url.path == "/" or parsed_url.path == "/events":
            self._send_html(self._render_events_page())
            return

        if parsed_url.path.startswith("/logs/"):
            self._send_log_file(parsed_url.path.removeprefix("/logs/"))
            return

        self.send_error(HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:
        parsed_url = urlparse(self.path)

        if parsed_url.path == "/events/delete-all":
            self._delete_all_events_and_logs()
            self._redirect("/")
            return

        if parsed_url.path == "/options/monitoring":
            form_values = self._get_form_values()
            self._save_monitoring_options(form_values)
            redirect_to = form_values.get("redirect_to", ["/"])[0].strip() or "/"
            self._redirect(redirect_to)
            return

        self.send_error(HTTPStatus.NOT_FOUND)

    def log_message(self, format: str, *args: object) -> None:
        print(f"Web UI: {format % args}")

    def _send_html(self, body: str, status: HTTPStatus = HTTPStatus.OK) -> None:
        content = body.encode("utf-8")

        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def _send_text(self, body: str, status: HTTPStatus = HTTPStatus.OK) -> None:
        content = body.encode("utf-8")

        self.send_response(status)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def _redirect(self, location: str) -> None:
        self.send_response(HTTPStatus.SEE_OTHER)
        self.send_header("Location", location)
        self.end_headers()

    def _send_log_file(self, raw_filename: str) -> None:
        filename = unquote(raw_filename)
        log_path = (LOG_DIR / filename).resolve()

        if not self._is_safe_log_path(log_path) or not log_path.is_file():
            self.send_error(HTTPStatus.NOT_FOUND)
            return

        self._send_text(log_path.read_text(encoding="utf-8", errors="replace"))

    def _is_safe_log_path(self, log_path: Path) -> bool:
        return log_path == LOG_DIR or LOG_DIR in log_path.parents

    def _delete_all_events_and_logs(self) -> None:
        delete_all_events()

        try:
            if LOG_DIR.exists():
                rmtree(LOG_DIR)
        except OSError as error:
            print(f"Could not delete log files: {error}")

    def _save_monitoring_options(self, form_values: dict[str, list[str]]) -> None:
        actions = {
            action
            for raw_action in form_values.get("actions", [])
            if (action := DockerEventAction.from_raw(raw_action)) is not None
        }

        replace_monitored_event_actions(actions)

    def _render_events_page(self) -> str:
        container_filter = self._get_container_filter()
        start_filter = self._get_query_value("start")
        end_filter = self._get_query_value("end")
        monitored_actions = select_monitored_event_actions()
        events = self._select_events(start_filter, end_filter)
        events = self._filter_events(events, container_filter)
        rows = "\n".join(self._render_event_row(event) for event in events)

        if not rows:
            rows = """
                <tr>
                    <td colspan="7" class="empty">No Docker events recorded yet.</td>
                </tr>
            """

        options_modal = self._render_options_modal(monitored_actions)

        return f"""<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Docker Watcher</title>
    <style>
        :root {{
            color-scheme: light;
            --background: #f6f8fb;
            --surface: #ffffff;
            --line: #d9e0ea;
            --text: #172033;
            --muted: #607087;
            --accent: #1677c8;
        }}

        * {{
            box-sizing: border-box;
        }}

        body {{
            margin: 0;
            background: var(--background);
            color: var(--text);
            font-family: Arial, Helvetica, sans-serif;
            font-size: 14px;
        }}

        header {{
            padding: 20px 24px 12px;
            border-bottom: 1px solid var(--line);
            background: var(--surface);
        }}

        h1 {{
            margin: 0 0 4px;
            font-size: 22px;
            font-weight: 700;
        }}

        .subtitle {{
            margin: 0;
            color: var(--muted);
        }}

        main {{
            padding: 18px 24px 28px;
        }}

        .toolbar {{
            display: flex;
            align-items: end;
            justify-content: space-between;
            gap: 12px;
            margin-bottom: 14px;
            flex-wrap: wrap;
        }}

        .filter-form {{
            display: flex;
            gap: 8px;
            align-items: end;
            flex-wrap: wrap;
        }}

        label {{
            display: grid;
            gap: 4px;
            color: var(--muted);
            font-size: 12px;
            font-weight: 700;
            text-transform: uppercase;
        }}

        input {{
            width: 280px;
            max-width: calc(100vw - 48px);
            padding: 8px 10px;
            border: 1px solid var(--line);
            background: var(--surface);
            color: var(--text);
            font: inherit;
        }}

        input[type="checkbox"] {{
            width: auto;
            max-width: none;
            padding: 0;
        }}

        button,
        .button {{
            display: inline-flex;
            align-items: center;
            min-height: 36px;
            padding: 8px 12px;
            border: 1px solid var(--line);
            background: var(--surface);
            color: var(--text);
            font: inherit;
            font-weight: 700;
            cursor: pointer;
        }}

        .primary {{
            border-color: var(--accent);
            background: var(--accent);
            color: #ffffff;
        }}

        .danger {{
            border-color: #c63c3c;
            background: #c63c3c;
            color: #ffffff;
        }}

        .table-wrap {{
            overflow-x: auto;
            border: 1px solid var(--line);
            background: var(--surface);
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
            min-width: 920px;
        }}

        th,
        td {{
            padding: 10px 12px;
            border-bottom: 1px solid var(--line);
            text-align: left;
            vertical-align: top;
        }}

        th {{
            background: #edf2f7;
            color: #33445c;
            font-size: 12px;
            text-transform: uppercase;
        }}

        code {{
            font-family: Consolas, Monaco, monospace;
            font-size: 13px;
        }}

        a {{
            color: var(--accent);
            text-decoration: none;
            font-weight: 600;
        }}

        a:hover {{
            text-decoration: underline;
        }}

        .muted {{
            color: var(--muted);
        }}

        .empty {{
            color: var(--muted);
            padding: 28px 12px;
            text-align: center;
        }}

        .modal {{
            display: none;
            position: fixed;
            inset: 0;
            z-index: 10;
            background: rgba(23, 32, 51, 0.42);
            padding: 24px;
            overflow-y: auto;
        }}

        .modal:target {{
            display: block;
        }}

        .modal-panel {{
            width: min(760px, 100%);
            margin: 0 auto;
            background: var(--surface);
            border: 1px solid var(--line);
        }}

        .modal-header,
        .modal-footer {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 12px;
            padding: 14px 16px;
            border-bottom: 1px solid var(--line);
        }}

        .modal-footer {{
            justify-content: flex-end;
            border-top: 1px solid var(--line);
            border-bottom: 0;
        }}

        .modal-title {{
            margin: 0;
            font-size: 16px;
        }}

        .options-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 8px 14px;
            padding: 16px;
        }}

        .checkbox-label {{
            display: flex;
            align-items: center;
            gap: 8px;
            min-height: 28px;
            color: var(--text);
            font-size: 13px;
            font-weight: 600;
            text-transform: none;
        }}
    </style>
</head>
<body>
    <header>
        <h1>Docker Watcher</h1>
        <p class="subtitle">{len(events)} recorded event(s).</p>
    </header>
    <main>
        <div class="toolbar">
            <form class="filter-form" method="get" action="/">
                <label>
                    Container filter
                    <input
                        type="search"
                        name="container"
                        value="{escape(container_filter)}"
                        placeholder="name or container id"
                    >
                </label>
                <label>
                    From
                    <input
                        type="datetime-local"
                        name="start"
                        value="{escape(start_filter)}"
                    >
                </label>
                <label>
                    To
                    <input
                        type="datetime-local"
                        name="end"
                        value="{escape(end_filter)}"
                    >
                </label>
                <button class="primary" type="submit">Filter</button>
                <a class="button" href="{escape(self.path)}">Refresh</a>
                <a class="button" href="/">Clear</a>
            </form>
            <div class="filter-form">
                <a class="button" href="#options">Options</a>
                <form method="post" action="/events/delete-all">
                    <button class="danger" type="submit">Delete all</button>
                </form>
            </div>
        </div>
        <div class="table-wrap">
            <table>
                <thead>
                    <tr>
                        <th>ID</th>
                        <th>Date</th>
                        <th>Container</th>
                        <th>Container ID</th>
                        <th>Action</th>
                        <th>Exit Code</th>
                        <th>Logs</th>
                    </tr>
                </thead>
                <tbody>
                    {rows}
                </tbody>
            </table>
        </div>
    </main>
    {options_modal}
</body>
</html>"""

    def _render_options_modal(self, monitored_actions: set[DockerEventAction]) -> str:
        checkboxes = "\n".join(
            self._render_action_checkbox(action, monitored_actions)
            for action in CONTAINER_EVENT_ACTIONS
        )

        return f"""
    <div class="modal" id="options">
        <form class="modal-panel" method="post" action="/options/monitoring">
            <div class="modal-header">
                <h2 class="modal-title">Monitoring options</h2>
                <a class="button" href="{escape(self.path)}">Close</a>
            </div>
            <div class="options-grid">
                {checkboxes}
            </div>
            <div class="modal-footer">
                <input
                    type="hidden"
                    name="redirect_to"
                    value="{escape(self.path)}"
                >
                <a class="button" href="{escape(self.path)}">Cancel</a>
                <button class="primary" type="submit">Save</button>
            </div>
        </form>
    </div>
        """

    def _render_action_checkbox(
        self,
        action: DockerEventAction,
        monitored_actions: set[DockerEventAction],
    ) -> str:
        checked = " checked" if action in monitored_actions else ""
        label = action.value.replace("_", " ")

        return f"""
            <label class="checkbox-label">
                <input
                    type="checkbox"
                    name="actions"
                    value="{escape(action.value)}"{checked}
                >
                {escape(label)}
            </label>
        """

    def _get_container_filter(self) -> str:
        return self._get_query_value("container")

    def _get_query_value(self, name: str) -> str:
        query = parse_qs(urlparse(self.path).query)
        return query.get(name, [""])[0].strip()

    def _get_form_values(self) -> dict[str, list[str]]:
        content_length = int(self.headers.get("Content-Length", "0"))

        if content_length == 0:
            return {}

        body = self.rfile.read(content_length).decode("utf-8")
        return parse_qs(body)

    def _select_events(self, start_filter: str, end_filter: str) -> list[object]:
        start_timestamp = self._datetime_local_to_iso(start_filter)
        end_timestamp = self._datetime_local_to_iso(end_filter)

        if start_timestamp or end_timestamp:
            return select_events_between(
                start_timestamp or "0001-01-01T00:00:00",
                end_timestamp or "9999-12-31T23:59:59",
            )

        return select_all_events()

    def _datetime_local_to_iso(self, value: str) -> str:
        if not value:
            return ""

        return value if "T" in value else value.replace(" ", "T")

    def _filter_events(self, events: list[object], container_filter: str) -> list[object]:
        if not container_filter:
            return events

        normalized_filter = container_filter.lower()

        return [
            event for event in events
            if normalized_filter in getattr(event, "container_name", "").lower()
            or normalized_filter in getattr(event, "container_id", "").lower()
        ]

    def _render_event_row(self, event: object) -> str:
        log_link = self._render_log_link(getattr(event, "log_file_path", None))

        return f"""
            <tr>
                <td>{escape(str(getattr(event, "id", "") or ""))}</td>
                <td>{escape(getattr(event, "created_at", ""))}</td>
                <td>{escape(getattr(event, "container_name", ""))}</td>
                <td><code>{escape(getattr(event, "container_id", "")[:12])}</code></td>
                <td>{escape(getattr(event, "action", ""))}</td>
                <td>{escape(str(getattr(event, "exit_code", "") or ""))}</td>
                <td>{log_link}</td>
            </tr>
        """

    def _render_log_link(self, log_file_path: str | None) -> str:
        if not log_file_path:
            return '<span class="muted">No log file</span>'

        filename = Path(log_file_path).name
        return f'<a href="/logs/{escape(filename)}">Open logs</a>'


def run_web_server() -> None:
    server = ThreadingHTTPServer((WEB_HOST, WEB_PORT), EventLogRequestHandler)
    print(f"Docker Watcher web UI is available on port {WEB_PORT}.")
    server.serve_forever()


def start_web_server() -> Thread:
    thread = Thread(target=run_web_server, daemon=True)
    thread.start()
    return thread

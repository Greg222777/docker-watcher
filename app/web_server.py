import os
from html import escape
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from shutil import rmtree
from threading import Thread
from urllib.parse import parse_qs, unquote, urlparse

from app.database import delete_all_events, select_all_events

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
        if self.path == "/events/delete-all":
            self._delete_all_events_and_logs()
            self._redirect("/")
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

    def _render_events_page(self) -> str:
        container_filter = self._get_container_filter()
        events = self._filter_events(select_all_events(), container_filter)
        rows = "\n".join(self._render_event_row(event) for event in events)

        if not rows:
            rows = """
                <tr>
                    <td colspan="7" class="empty">No Docker events recorded yet.</td>
                </tr>
            """

        return f"""<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <meta http-equiv="refresh" content="15">
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
    </style>
</head>
<body>
    <header>
        <h1>Docker Watcher</h1>
        <p class="subtitle">{len(events)} recorded event(s). Auto-refresh every 15 seconds.</p>
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
                <button class="primary" type="submit">Filter</button>
                <a class="button" href="/">Clear</a>
            </form>
            <form method="post" action="/events/delete-all">
                <button class="danger" type="submit">Delete all</button>
            </form>
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
</body>
</html>"""

    def _get_container_filter(self) -> str:
        query = parse_qs(urlparse(self.path).query)
        return query.get("container", [""])[0].strip()

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

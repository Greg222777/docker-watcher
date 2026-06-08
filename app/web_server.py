import logging
import os
from pathlib import Path
from shutil import rmtree
from threading import Thread
from urllib.parse import urlencode

from flask import Flask, abort, redirect, render_template, request, send_file

from app.config import LOG_DIR
from app.database import event_log_repository, monitored_event_action_repository
from app.models import DockerEventAction, WATCHED_DOCKER_ACTIONS

WEB_HOST = "0.0.0.0"
WEB_PORT = int(os.getenv("WEB_PORT", "8000"))
EVENTS_PER_PAGE = 2
logger = logging.getLogger(__name__)

app = Flask(__name__)


@app.template_filter("basename")
def basename(value: str) -> str:
    return Path(value).name


@app.get("/")
@app.get("/events")
def events_page() -> str:
    container_filter = request.args.get("container", "").strip()
    event_filter = request.args.get("event", "").strip()
    start_filter = request.args.get("start", "").strip()
    end_filter = request.args.get("end", "").strip()
    page = _positive_int(request.args.get("page"), default=1)
    start_timestamp = _datetime_local_to_iso(start_filter)
    end_timestamp = _datetime_local_to_iso(end_filter)
    selected_action = DockerEventAction.from_raw(event_filter)
    action_filter = selected_action.value if selected_action else ""
    total_events = event_log_repository.count_filtered(
        start_timestamp=start_timestamp,
        end_timestamp=end_timestamp,
        container_filter=container_filter,
        action_filter=action_filter,
    )
    total_pages = max(1, (total_events + EVENTS_PER_PAGE - 1) // EVENTS_PER_PAGE)
    page = min(page, total_pages)
    events = event_log_repository.select_filtered(
        start_timestamp=start_timestamp,
        end_timestamp=end_timestamp,
        container_filter=container_filter,
        action_filter=action_filter,
        limit=EVENTS_PER_PAGE,
        offset=(page - 1) * EVENTS_PER_PAGE,
    )

    return render_template(
        "events.html",
        actions=WATCHED_DOCKER_ACTIONS,
        container_filter=container_filter,
        current_path=_current_path(),
        end_filter=end_filter,
        event_filter=event_filter,
        events=events,
        monitored_actions=monitored_event_action_repository.select_all(),
        page=page,
        page_url=_page_url,
        per_page=EVENTS_PER_PAGE,
        start_filter=start_filter,
        total_events=total_events,
        total_pages=total_pages,
    )


@app.get("/logs/<path:filename>")
def log_file(filename: str):
    log_path = (LOG_DIR / filename).resolve()

    if not _is_safe_log_path(log_path) or not log_path.is_file():
        abort(404)

    return send_file(log_path, mimetype="text/plain")


@app.post("/events/delete-all")
def delete_all_events():
    event_log_repository.delete_all()

    try:
        if LOG_DIR.exists():
            rmtree(LOG_DIR)
    except OSError as error:
        logger.error("Could not delete log files: %s", error)

    return redirect("/")


@app.post("/options/monitoring")
def save_monitoring_options():
    actions = {
        action
        for raw_action in request.form.getlist("actions")
        if (action := DockerEventAction.from_raw(raw_action)) is not None
    }

    monitored_event_action_repository.replace_all(actions)

    return redirect(_safe_redirect_path(request.form.get("redirect_to", "/")))


def _datetime_local_to_iso(value: str) -> str:
    if not value:
        return ""

    return value if "T" in value else value.replace(" ", "T")


def _is_safe_log_path(log_path: Path) -> bool:
    return log_path == LOG_DIR or LOG_DIR in log_path.parents


def _current_path() -> str:
    return request.full_path.rstrip("?")


def _safe_redirect_path(path: str) -> str:
    return path if path.startswith("/") and not path.startswith("//") else "/"


def _positive_int(value: str | None, default: int) -> int:
    try:
        parsed_value = int(value or "")
    except ValueError:
        return default

    return parsed_value if parsed_value > 0 else default


def _page_url(page: int) -> str:
    args = request.args.to_dict()
    args["page"] = str(page)
    return f"{request.path}?{urlencode(args)}"


def run_web_server() -> None:
    logger.info("Docker Watcher web UI is available on port %s.", WEB_PORT)
    app.run(
        host=WEB_HOST,
        port=WEB_PORT,
        threaded=True,
        use_reloader=False,
    )


def start_web_server() -> Thread:
    thread = Thread(target=run_web_server, daemon=True)
    thread.start()
    return thread

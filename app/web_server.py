import logging
import os
from pathlib import Path
from shutil import rmtree
from threading import Thread

from flask import Flask, abort, redirect, render_template, request, send_file

from app.config import LOG_DIR
from app.database import event_log_repository, monitored_event_action_repository
from app.models import DockerEventAction, EventLog, WATCHED_DOCKER_ACTIONS

WEB_HOST = "0.0.0.0"
WEB_PORT = int(os.getenv("WEB_PORT", "8000"))
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
    events = _select_events(start_filter, end_filter)
    events = _filter_events(events, container_filter, event_filter)

    return render_template(
        "events.html",
        actions=WATCHED_DOCKER_ACTIONS,
        container_filter=container_filter,
        current_path=_current_path(),
        end_filter=end_filter,
        event_filter=event_filter,
        events=events,
        monitored_actions=monitored_event_action_repository.select_all(),
        start_filter=start_filter,
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


def _select_events(start_filter: str, end_filter: str) -> list[EventLog]:
    start_timestamp = _datetime_local_to_iso(start_filter)
    end_timestamp = _datetime_local_to_iso(end_filter)

    if start_timestamp or end_timestamp:
        return event_log_repository.select_between(
            start_timestamp or "0001-01-01T00:00:00",
            end_timestamp or "9999-12-31T23:59:59",
        )

    return event_log_repository.select_all()


def _datetime_local_to_iso(value: str) -> str:
    if not value:
        return ""

    return value if "T" in value else value.replace(" ", "T")


def _filter_events(
    events: list[EventLog],
    container_filter: str,
    event_filter: str,
) -> list[EventLog]:
    selected_action = DockerEventAction.from_raw(event_filter)

    if not container_filter and selected_action is None:
        return events

    normalized_filter = container_filter.lower()

    return [
        event for event in events
        if _matches_container_filter(event, normalized_filter)
        and _matches_event_filter(event, selected_action)
    ]


def _matches_container_filter(event: EventLog, container_filter: str) -> bool:
    if not container_filter:
        return True

    return (
        container_filter in event.container_name.lower()
        or container_filter in event.container_id.lower()
    )


def _matches_event_filter(
    event: EventLog,
    selected_action: DockerEventAction | None,
) -> bool:
    if selected_action is None:
        return True

    return selected_action.matches(event.action)


def _is_safe_log_path(log_path: Path) -> bool:
    return log_path == LOG_DIR or LOG_DIR in log_path.parents


def _current_path() -> str:
    return request.full_path.rstrip("?")


def _safe_redirect_path(path: str) -> str:
    return path if path.startswith("/") and not path.startswith("//") else "/"


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

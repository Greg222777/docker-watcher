import logging
import os
from datetime import time
from pathlib import Path
from shutil import rmtree

from flask import (
    Flask,
    abort,
    jsonify,
    redirect,
    render_template,
    request,
    send_file,
    url_for,
)

from app.ai_log_analyzer import AILogAnalysisError, analyze_event_log
from app.config import LOG_DIR
from app.database import (
    event_log_repository,
    monitored_event_action_repository,
    telegram_options_repository,
)
from app.models.docker_event_action import WATCHED_DOCKER_ACTIONS, DockerEventAction
from app.models.event_log import EventLog
from app.models.telegram_options import TelegramOptions

WEB_HOST = "0.0.0.0"
WEB_PORT = int(os.getenv("WEB_PORT", "8000"))
EVENTS_PER_PAGE = 50
logger = logging.getLogger(__name__)

app = Flask(__name__)


@app.template_filter("basename")
def basename(value: str) -> str:
    return Path(value).name


# Event list
@app.get("/")
@app.get("/events")
def events_page() -> str:
    container_filter = request.args.get("container", "").strip()
    event_filter = request.args.get("event", "").strip()
    start_filter = request.args.get("start", "").strip()
    end_filter = request.args.get("end", "").strip()
    selected_action = DockerEventAction.from_raw(event_filter)
    action_filter = selected_action.value if selected_action else ""
    start_timestamp = _datetime_local_to_iso(start_filter)
    end_timestamp = _datetime_local_to_iso(end_filter)

    total_events = event_log_repository.count_filtered(
        start_timestamp=start_timestamp,
        end_timestamp=end_timestamp,
        container_filter=container_filter,
        action_filter=action_filter,
    )
    page, total_pages = _pagination_for(
        total_events=total_events,
        requested_page=_positive_int(request.args.get("page"), default=1),
    )
    offset = (page - 1) * EVENTS_PER_PAGE
    events = event_log_repository.select_filtered(
        start_timestamp=start_timestamp,
        end_timestamp=end_timestamp,
        container_filter=container_filter,
        action_filter=action_filter,
        limit=EVENTS_PER_PAGE,
        offset=offset,
    )

    return render_template(
        "events.html",
        actions=WATCHED_DOCKER_ACTIONS,
        container_filter=container_filter,
        current_path=request.full_path.rstrip("?"),
        end_filter=end_filter,
        event_filter=event_filter,
        events=events,
        monitored_actions=monitored_event_action_repository.select_all(),
        page=page,
        per_page=EVENTS_PER_PAGE,
        start_filter=start_filter,
        telegram_options=telegram_options_repository.select(),
        total_events=total_events,
        total_pages=total_pages,
        url_for_page=_url_for_page,
    )


# Log files and AI analysis
@app.get("/logs/<path:filename>")
def log_file(filename: str):
    log_path = _log_path(filename)

    if not _is_safe_log_path(log_path) or not log_path.is_file():
        abort(404)

    return send_file(log_path, mimetype="text/plain")


@app.get("/events/<int:event_id>/ai-analysis")
def ai_log_analysis(event_id: int):
    event, log_path = _event_log(event_id)

    return render_template(
        "ai_analysis.html",
        analysis_result_url=url_for("ai_log_analysis_result", event_id=event_id),
        event=event,
        log_filename=log_path.name,
    )


@app.get("/events/<int:event_id>/ai-analysis/result")
def ai_log_analysis_result(event_id: int):
    event, log_path = _event_log(event_id)

    try:
        analysis = analyze_event_log(event=event, log_path=log_path)
    except AILogAnalysisError as error:
        return jsonify({"error": f"AI log analysis failed: {error}"}), 503

    return jsonify({"analysis": analysis})


# Mutations
@app.post("/events/delete-all")
def delete_all_events():
    event_log_repository.delete_all()

    try:
        if LOG_DIR.exists():
            rmtree(LOG_DIR)
    except OSError as error:
        logger.error("Could not delete log files: %s", error)

    return redirect(url_for("events_page"))


@app.post("/options/monitoring")
def save_monitoring_options():
    actions = {
        action
        for raw_action in request.form.getlist("actions")
        if (action := DockerEventAction.from_raw(raw_action)) is not None
    }

    monitored_event_action_repository.replace_all(actions)
    telegram_options_repository.save(
        TelegramOptions(
            receive_daily_status=request.form.get("receive_daily_status") == "on",
            daily_status_time=_valid_time(
                request.form.get("daily_status_time", ""),
                default="09:00",
            ),
            receive_event_notifications=(
                request.form.get("receive_event_notifications") == "on"
            ),
        )
    )

    return redirect(_safe_redirect_path(request.form.get("redirect_to", "/")))


# Request helpers
def _datetime_local_to_iso(value: str) -> str:
    if not value:
        return ""

    return value if "T" in value else value.replace(" ", "T")


def _positive_int(value: str | None, default: int) -> int:
    try:
        parsed_value = int(value or "")
    except ValueError:
        return default

    return parsed_value if parsed_value > 0 else default


def _valid_time(value: str, default: str) -> str:
    try:
        time.fromisoformat(value)
    except ValueError:
        return default

    return value


def _pagination_for(total_events: int, requested_page: int) -> tuple[int, int]:
    total_pages = max(1, (total_events + EVENTS_PER_PAGE - 1) // EVENTS_PER_PAGE)

    return min(requested_page, total_pages), total_pages


def _url_for_page(page: int) -> str:
    args = request.args.to_dict()
    args["page"] = str(page)
    endpoint = request.endpoint or "events_page"

    # Flask route args are dynamic; mypy only knows url_for's reserved kwargs.
    return url_for(endpoint, **args)  # type: ignore[arg-type]


# Path helpers
def _safe_redirect_path(path: str) -> str:
    return path if path.startswith("/") and not path.startswith("//") else "/"


def _is_safe_log_path(log_path: Path) -> bool:
    return log_path == LOG_DIR or LOG_DIR in log_path.parents


def _log_path(filename: str) -> Path:
    # Only trust the filename; event log paths may come from stored records.
    return (LOG_DIR / Path(filename).name).resolve()


def _event_log(event_id: int) -> tuple[EventLog, Path]:
    event = event_log_repository.select_by_id(event_id)

    if not event or not event.log_file_path:
        abort(404)

    log_path = _log_path(event.log_file_path)

    # The file may have been deleted after the event was stored.
    if not _is_safe_log_path(log_path) or not log_path.is_file():
        abort(404)

    return event, log_path


# Server lifecycle
def run_web_server() -> None:
    logger.info("Docker Watcher web UI is available on port %s.", WEB_PORT)
    app.run(
        host=WEB_HOST,
        port=WEB_PORT,
        threaded=True,
        use_reloader=False,
    )

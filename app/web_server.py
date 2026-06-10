import logging
import os
from dataclasses import dataclass
from pathlib import Path
from shutil import rmtree
from threading import Thread

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

from app.ai_log_analyzer import AILogAnalysisError, OpenAILogAnalyzer
from app.config import LOG_DIR
from app.database import event_log_repository, monitored_event_action_repository
from app.models import WATCHED_DOCKER_ACTIONS, DockerEventAction

WEB_HOST = "0.0.0.0"
WEB_PORT = int(os.getenv("WEB_PORT", "8000"))
EVENTS_PER_PAGE = 50
logger = logging.getLogger(__name__)

app = Flask(__name__)


@dataclass(frozen=True)
class EventFilters:
    container: str
    event: str
    start: str
    end: str
    start_timestamp: str
    end_timestamp: str
    action: str


@dataclass(frozen=True)
class Pagination:
    page: int
    per_page: int
    total_pages: int

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.per_page


@app.template_filter("basename")
def basename(value: str) -> str:
    return Path(value).name


@app.get("/")
@app.get("/events")
def events_page() -> str:
    filters = _event_filters_from_request()
    total_events = event_log_repository.count_filtered(
        start_timestamp=filters.start_timestamp,
        end_timestamp=filters.end_timestamp,
        container_filter=filters.container,
        action_filter=filters.action,
    )
    pagination = _pagination_for(
        total_events=total_events,
        requested_page=_positive_int(request.args.get("page"), default=1),
    )
    events = event_log_repository.select_filtered(
        start_timestamp=filters.start_timestamp,
        end_timestamp=filters.end_timestamp,
        container_filter=filters.container,
        action_filter=filters.action,
        limit=pagination.per_page,
        offset=pagination.offset,
    )

    return render_template(
        "events.html",
        actions=WATCHED_DOCKER_ACTIONS,
        container_filter=filters.container,
        current_path=_current_path(),
        end_filter=filters.end,
        event_filter=filters.event,
        events=events,
        monitored_actions=monitored_event_action_repository.select_all(),
        page=pagination.page,
        per_page=pagination.per_page,
        start_filter=filters.start,
        total_events=total_events,
        total_pages=pagination.total_pages,
        url_for_page=_url_for_page,
    )


@app.get("/logs/<path:filename>")
def log_file(filename: str):
    log_path = (LOG_DIR / filename).resolve()

    if not _is_safe_log_path(log_path) or not log_path.is_file():
        abort(404)

    return send_file(log_path, mimetype="text/plain")


@app.get("/events/<int:event_id>/ai-analysis")
def ai_log_analysis(event_id: int):
    event, log_path = _event_and_log_path_or_404(event_id)

    return render_template(
        "ai_analysis.html",
        analysis_result_url=url_for("ai_log_analysis_result", event_id=event_id),
        event=event,
        log_filename=log_path.name,
    )


@app.get("/events/<int:event_id>/ai-analysis/result")
def ai_log_analysis_result(event_id: int):
    event, log_path = _event_and_log_path_or_404(event_id)

    try:
        analysis = OpenAILogAnalyzer().analyze_event_log(event=event, log_path=log_path)
    except AILogAnalysisError as error:
        return jsonify({"error": f"AI log analysis failed: {error}"}), 503

    return jsonify({"analysis": analysis})


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

    return redirect(_safe_redirect_path(request.form.get("redirect_to", "/")))


# Request parsing and filter normalization
def _event_filters_from_request() -> EventFilters:
    container_filter = request.args.get("container", "").strip()
    event_filter = request.args.get("event", "").strip()
    start_filter = request.args.get("start", "").strip()
    end_filter = request.args.get("end", "").strip()
    selected_action = DockerEventAction.from_raw(event_filter)

    return EventFilters(
        container=container_filter,
        event=event_filter,
        start=start_filter,
        end=end_filter,
        start_timestamp=_datetime_local_to_iso(start_filter),
        end_timestamp=_datetime_local_to_iso(end_filter),
        action=selected_action.value if selected_action else "",
    )


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


# Pagination
def _pagination_for(total_events: int, requested_page: int) -> Pagination:
    total_pages = max(1, (total_events + EVENTS_PER_PAGE - 1) // EVENTS_PER_PAGE)

    return Pagination(
        page=min(requested_page, total_pages),
        per_page=EVENTS_PER_PAGE,
        total_pages=total_pages,
    )


def _url_for_page(page: int) -> str:
    args = request.args.to_dict()
    args["page"] = str(page)
    endpoint = request.endpoint or "events_page"

    return url_for(endpoint, **args)


# Path safety and redirects
def _safe_redirect_path(path: str) -> str:
    return path if path.startswith("/") and not path.startswith("//") else "/"


def _is_safe_log_path(log_path: Path) -> bool:
    return log_path == LOG_DIR or LOG_DIR in log_path.parents


def _event_and_log_path_or_404(event_id: int):
    event = event_log_repository.select_by_id(event_id)

    if not event or not event.log_file_path:
        abort(404)

    log_path = (LOG_DIR / Path(event.log_file_path).name).resolve()

    if not _is_safe_log_path(log_path) or not log_path.is_file():
        abort(404)

    return event, log_path


def _current_path() -> str:
    return request.full_path.rstrip("?")


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

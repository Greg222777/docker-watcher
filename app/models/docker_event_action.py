from enum import StrEnum


class DockerEventAction(StrEnum):
    """
    Docker event actions documented by `docker system events`.

    Source:
    https://docs.docker.com/reference/cli/docker/system/events/

    This enum contains the distinct container action values documented by the
    Docker CLI. The listener filters Docker events to containers only.

    Note: container health events are documented as `health_status`, but Docker
    can emit detail values such as `health_status: healthy` or
    `health_status: unhealthy`. Use `matches()` when comparing raw event actions.
    """

    ATTACH = "attach"
    COMMIT = "commit"
    COPY = "copy"
    CREATE = "create"
    DESTROY = "destroy"
    DETACH = "detach"
    DIE = "die"
    EXEC_CREATE = "exec_create"
    EXEC_DETACH = "exec_detach"
    EXEC_DIE = "exec_die"
    EXEC_START = "exec_start"
    EXPORT = "export"
    HEALTH_STATUS = "health_status"
    KILL = "kill"
    OOM = "oom"
    PAUSE = "pause"
    RENAME = "rename"
    RESIZE = "resize"
    RESTART = "restart"
    START = "start"
    STOP = "stop"
    TOP = "top"
    UNPAUSE = "unpause"
    UPDATE = "update"

    @classmethod
    def normalize(cls, action: str) -> str:
        """
        Return the documented action value for a raw Docker event action.

        Docker can include health details after the action prefix, for example
        `health_status: healthy`. That still represents the documented
        `health_status` action.
        """
        return action.split(":", 1)[0].strip()

    @classmethod
    def from_raw(cls, action: str) -> "DockerEventAction | None":
        """
        Convert a raw Docker action string to an enum member when documented.
        """
        normalized_action = cls.normalize(action)

        try:
            return cls(normalized_action)
        except ValueError:
            return None

    def matches(self, action: str) -> bool:
        """
        Return True when this documented action matches a raw Docker action.
        """
        return self.value == self.normalize(action)


WATCHED_DOCKER_ACTIONS = [
    DockerEventAction.ATTACH,
    DockerEventAction.COMMIT,
    DockerEventAction.COPY,
    DockerEventAction.CREATE,
    DockerEventAction.DESTROY,
    DockerEventAction.DETACH,
    DockerEventAction.DIE,
    DockerEventAction.EXEC_CREATE,
    DockerEventAction.EXEC_DETACH,
    DockerEventAction.EXEC_DIE,
    DockerEventAction.EXEC_START,
    DockerEventAction.EXPORT,
    DockerEventAction.HEALTH_STATUS,
    DockerEventAction.KILL,
    DockerEventAction.OOM,
    DockerEventAction.PAUSE,
    DockerEventAction.RENAME,
    DockerEventAction.RESIZE,
    DockerEventAction.RESTART,
    DockerEventAction.START,
    DockerEventAction.STOP,
    DockerEventAction.TOP,
    DockerEventAction.UNPAUSE,
    DockerEventAction.UPDATE,
]

DEFAULT_MONITORED_EVENT_ACTIONS = {
    DockerEventAction.DESTROY,
    DockerEventAction.DIE,
    DockerEventAction.EXEC_DIE,
    DockerEventAction.HEALTH_STATUS,
    DockerEventAction.KILL,
    DockerEventAction.OOM,
    DockerEventAction.PAUSE,
    DockerEventAction.RESTART,
    DockerEventAction.STOP,
}

from typing import Any, Protocol


DockerEvent = dict[str, Any]


class DockerClient(Protocol):
    def events(self, **kwargs: Any) -> Any:
        ...

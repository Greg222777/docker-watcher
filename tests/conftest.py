import sys
import types
from collections.abc import Generator
from pathlib import Path
from unittest.mock import Mock

import pytest

if "docker" not in sys.modules:
    docker_module = types.ModuleType("docker")
    docker_errors_module = types.ModuleType("docker.errors")

    class APIError(Exception):
        pass

    class DockerException(Exception):
        pass

    class NotFound(Exception):
        pass

    setattr(docker_module, "from_env", Mock())
    setattr(docker_errors_module, "APIError", APIError)
    setattr(docker_errors_module, "DockerException", DockerException)
    setattr(docker_errors_module, "NotFound", NotFound)
    sys.modules["docker"] = docker_module
    sys.modules["docker.errors"] = docker_errors_module


@pytest.fixture
def test_log_dir() -> Generator[Path]:
    log_dir = Path(__file__).resolve().parent / "logs"
    log_dir.mkdir(exist_ok=True)

    for file_path in log_dir.iterdir():
        if file_path.is_file():
            file_path.unlink()

    yield log_dir

    for file_path in log_dir.iterdir():
        if file_path.is_file():
            file_path.unlink()

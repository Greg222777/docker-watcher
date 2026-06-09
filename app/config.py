import os
from pathlib import Path

DATA_DIR = Path(os.getenv("DATA_DIR", "/data")).resolve()
DB_PATH = DATA_DIR / "docker_events.db"
LOG_DIR = DATA_DIR / "logs"

from pathlib import Path

DATA_DIR = Path("/data").resolve()
DB_PATH = DATA_DIR / "docker_events.db"
LOG_DIR = DATA_DIR / "logs"

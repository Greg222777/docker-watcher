from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect

from app.config import DB_PATH
from app.database.session import build_database_url

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ALEMBIC_INI_PATH = PROJECT_ROOT / "alembic.ini"
MIGRATIONS_PATH = PROJECT_ROOT / "migrations"
ALEMBIC_VERSION_TABLE = "alembic_version"
APPLICATION_TABLES = {"container_events", "monitored_event_actions"}


def run_migrations(db_path: str | Path = DB_PATH) -> None:
    config = Config(str(ALEMBIC_INI_PATH))
    config.set_main_option("script_location", str(MIGRATIONS_PATH))
    config.set_main_option("sqlalchemy.url", build_database_url(db_path))

    if _has_unversioned_application_schema(db_path):
        command.stamp(config, "head")
        return

    command.upgrade(config, "head")


def _has_unversioned_application_schema(db_path: str | Path) -> bool:
    engine = create_engine(build_database_url(db_path), future=True)

    with engine.connect() as connection:
        # Databases up to 1.1 had application tables but no migration tracking table.
        table_names = set(inspect(connection).get_table_names())

    return ALEMBIC_VERSION_TABLE not in table_names and APPLICATION_TABLES.issubset(
        table_names
    )

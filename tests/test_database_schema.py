from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, inspect, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import NullPool

from app.database.schema import run_migrations
from app.database.session import build_database_url
from app.database.tables import (
    ContainerEventRecord,
    MonitoredEventActionRecord,
    SchemaMigrationRecord,
)

TEST_DIR = Path(__file__).resolve().parent


@pytest.fixture
def db_path() -> Path:
    path = TEST_DIR / f"schema_{uuid4().hex}.db"

    yield path

    try:
        if path.exists():
            path.unlink()
    except PermissionError:
        pass


def test_run_migrations_creates_schema(db_path) -> None:
    run_migrations(db_path)

    engine = _create_engine(db_path)

    with engine.connect() as connection:
        table_names = set(inspect(connection).get_table_names())

    assert "schema_migrations" in table_names
    assert "container_events" in table_names
    assert "monitored_event_actions" in table_names
    assert _select_revisions(db_path) == {"0001_initial_schema"}


def test_run_migrations_marks_existing_schema_as_applied(db_path) -> None:
    engine = _create_engine(db_path)

    with engine.begin() as connection:
        ContainerEventRecord.__table__.create(bind=connection)
        MonitoredEventActionRecord.__table__.create(bind=connection)

    run_migrations(db_path)

    assert _select_revisions(db_path) == {"0001_initial_schema"}


def _create_engine(db_path: Path):
    return create_engine(
        build_database_url(db_path),
        future=True,
        poolclass=NullPool,
    )


def _select_revisions(db_path: Path) -> set[str]:
    engine = _create_engine(db_path)

    with Session(engine) as session:
        revisions = session.scalars(select(SchemaMigrationRecord.revision))

        return set(revisions)

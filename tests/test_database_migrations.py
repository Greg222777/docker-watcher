from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import Column, MetaData, String, Table, create_engine, inspect, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import NullPool

from app.database.migrations import run_migrations
from app.database.session import build_database_url
from app.database.tables import ContainerEventRecord, MonitoredEventActionRecord

TEST_DIR = Path(__file__).resolve().parent


@pytest.fixture
def db_path() -> Path:
    path = TEST_DIR / f"migrations_{uuid4().hex}.db"

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

    assert "alembic_version" in table_names
    assert "container_events" in table_names
    assert "monitored_event_actions" in table_names


def test_run_migrations_stamps_existing_schema(db_path) -> None:
    engine = _create_engine(db_path)

    with engine.begin() as connection:
        ContainerEventRecord.__table__.create(bind=connection)
        MonitoredEventActionRecord.__table__.create(bind=connection)

    run_migrations(db_path)

    assert _select_alembic_version(db_path) == "0001"


def _create_engine(db_path: Path):
    return create_engine(
        build_database_url(db_path),
        future=True,
        poolclass=NullPool,
    )


def _select_alembic_version(db_path: Path) -> str:
    engine = _create_engine(db_path)
    alembic_version = Table(
        "alembic_version",
        MetaData(),
        Column("version_num", String, primary_key=True),
    )

    with Session(engine) as session:
        return str(session.scalar(select(alembic_version.c.version_num)))

from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, inspect
from sqlalchemy.pool import NullPool

from app.database.schema import init_schema
from app.database.session import build_database_url

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


def test_init_schema_creates_application_tables(db_path) -> None:
    init_schema(db_path)

    engine = create_engine(
        build_database_url(db_path),
        future=True,
        poolclass=NullPool,
    )

    with engine.connect() as connection:
        table_names = set(inspect(connection).get_table_names())

    assert table_names == {"container_events", "monitored_event_actions"}

from sqlalchemy import create_engine, inspect
from sqlalchemy.pool import NullPool

from app.database.schema import init_schema


def test_init_schema_creates_application_tables(tmp_path) -> None:
    db_path = tmp_path / "docker_events.db"
    init_schema(db_path)

    engine = create_engine(
        f"sqlite:///{db_path}",
        future=True,
        poolclass=NullPool,
    )

    with engine.connect() as connection:
        table_names = set(inspect(connection).get_table_names())

    assert table_names == {"container_events", "monitored_event_actions"}

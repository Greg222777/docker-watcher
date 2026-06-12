from collections.abc import Callable, Iterable
from pathlib import Path

from sqlalchemy import Connection, create_engine, inspect, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import NullPool

from app.config import DB_PATH
from app.database.session import build_database_url
from app.database.tables import (
    ContainerEventRecord,
    MonitoredEventActionRecord,
    SchemaMigrationRecord,
)

APPLICATION_TABLES = {"container_events", "monitored_event_actions"}
Migration = Callable[[Connection], None]


def _create_initial_schema(connection: Connection) -> None:
    ContainerEventRecord.__table__.create(bind=connection)
    MonitoredEventActionRecord.__table__.create(bind=connection)


MIGRATIONS: list[tuple[str, Migration]] = [
    ("0001_initial_schema", _create_initial_schema),
]


def run_migrations(db_path: str | Path = DB_PATH) -> None:
    engine = create_engine(
        build_database_url(db_path),
        future=True,
        poolclass=NullPool,
    )

    with engine.begin() as connection:
        SchemaMigrationRecord.__table__.create(bind=connection, checkfirst=True)
        session = Session(bind=connection)

        if _has_existing_unversioned_schema(connection, session):
            _mark_migrations_as_applied(
                session,
                (revision for revision, _migration in MIGRATIONS),
            )
            return

        applied_revisions = _select_applied_revisions(session)

        for revision, migration in MIGRATIONS:
            if revision not in applied_revisions:
                migration(connection)
                _mark_migrations_as_applied(session, [revision])


def _has_existing_unversioned_schema(
    connection: Connection,
    session: Session,
) -> bool:
    # Databases up to 1.1 had application tables but no migration tracking table.
    table_names = set(inspect(connection).get_table_names())

    if not APPLICATION_TABLES.issubset(table_names):
        return False

    applied_revisions = _select_applied_revisions(session)
    return len(applied_revisions) == 0


def _select_applied_revisions(session: Session) -> set[str]:
    revisions = session.scalars(select(SchemaMigrationRecord.revision))

    return set(revisions)


def _mark_migrations_as_applied(
    session: Session,
    revisions: Iterable[str],
) -> None:
    session.add_all(
        [SchemaMigrationRecord(revision=revision) for revision in revisions]
    )
    session.flush()

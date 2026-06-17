from pathlib import Path
from typing import cast

from sqlalchemy import Table, create_engine
from sqlalchemy.pool import NullPool

from app.config import DB_PATH
from app.database.session import Base, build_database_url
from app.database.tables import ContainerEventRecord, MonitoredEventActionRecord


def init_schema(db_path: str | Path = DB_PATH) -> None:
    engine = create_engine(
        build_database_url(db_path),
        future=True,
        poolclass=NullPool,
    )

    Base.metadata.create_all(
        engine,
        tables=[
            cast(Table, ContainerEventRecord.__table__),
            cast(Table, MonitoredEventActionRecord.__table__),
        ],
    )

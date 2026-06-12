from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy.pool import NullPool


class Base(DeclarativeBase):
    pass


def build_database_url(db_path: str | Path) -> str:
    return f"sqlite:///{Path(db_path)}"


def create_session_factory(db_path: str | Path) -> sessionmaker:
    engine = create_engine(
        build_database_url(db_path),
        future=True,
        poolclass=NullPool,
    )
    return sessionmaker(bind=engine, future=True)

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
import sys

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.paths import database_path

DATABASE_URL = f"sqlite:///{database_path().as_posix()}"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@event.listens_for(Engine, "connect")
def set_sqlite_pragmas(dbapi_connection, _connection_record) -> None:
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


def initialize_database() -> None:
    if _has_versioned_schema():
        _upgrade_database()
    elif _has_user_tables():
        _repair_legacy_schema()
        _stamp_database_head()
    else:
        _upgrade_database()

    with engine.connect() as connection:
        connection.execute(text("SELECT json('{}')"))


def _has_versioned_schema() -> bool:
    return "alembic_version" in inspect(engine).get_table_names()


def _has_user_tables() -> bool:
    table_names = set(inspect(engine).get_table_names())
    return any(not name.startswith("sqlite_") and name != "alembic_version" for name in table_names)


def _upgrade_database() -> None:
    command.upgrade(_alembic_config(), "head")


def _stamp_database_head() -> None:
    command.stamp(_alembic_config(), "head")


def _repair_legacy_schema() -> None:
    from app.db.models import Base

    Base.metadata.create_all(bind=engine)
    _ensure_column("chat_sessions", "target_id", "INTEGER")
    _ensure_column("conversations", "target_id", "INTEGER")


def _ensure_column(table_name: str, column_name: str, column_sql: str) -> None:
    inspector = inspect(engine)
    if table_name not in inspector.get_table_names():
        return
    column_names = {column["name"] for column in inspector.get_columns(table_name)}
    if column_name in column_names:
        return
    with engine.begin() as connection:
        connection.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_sql}"))


def _alembic_config() -> Config:
    config = Config()
    config.set_main_option("script_location", str(_migrations_path()))
    config.set_main_option("sqlalchemy.url", DATABASE_URL)
    return config


def _migrations_path() -> Path:
    candidates = []
    bundle_root = getattr(sys, "_MEIPASS", None)
    if bundle_root:
        candidates.append(Path(bundle_root) / "app" / "db" / "migrations")
    candidates.append(Path(__file__).resolve().parent / "migrations")

    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[-1]


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

import importlib.util
import re
from collections.abc import Iterator
from pathlib import Path
from types import ModuleType
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import Boolean, DateTime, Integer, SmallInteger, Text, create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.engine.url import make_url

from app.config import normalize_database_url
from app.db.models import Base
from tests.conftest import _clear_caches, _postgres_reachable, _test_database_url

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCHEMA_SQL = PROJECT_ROOT / "schema.sql"
BASELINE = PROJECT_ROOT / "migrations" / "versions" / "0001_focus_todo_baseline.py"
FOCUS_TODO_TABLES = {"projects", "tasks", "subtasks", "pomodoro_sessions"}


def _load_baseline() -> ModuleType:
    spec = importlib.util.spec_from_file_location("focus_todo_baseline", BASELINE)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _normalize_sql(sql: str) -> str:
    return re.sub(r"\s+", " ", sql).strip()


def _schema_sql_statements() -> list[str]:
    without_comments = re.sub(r"--[^\n]*", "", SCHEMA_SQL.read_text())
    return [_normalize_sql(s) for s in without_comments.split(";") if s.strip()]


def test_baseline_statements_match_schema_sql() -> None:
    baseline = _load_baseline()
    assert [_normalize_sql(s) for s in baseline.STATEMENTS] == _schema_sql_statements()


@pytest.fixture
def scratch_db(monkeypatch: pytest.MonkeyPatch) -> Iterator[tuple[Engine, Config]]:
    """An empty, uniquely named database on the throwaway test server."""
    server_url = normalize_database_url(_test_database_url())
    if not _postgres_reachable(server_url):
        pytest.skip(f"Postgres not reachable at {server_url}; set TEST_DATABASE_URL.")
    name = f"pomodoro_migration_{uuid4().hex[:12]}"
    admin = create_engine(server_url, isolation_level="AUTOCOMMIT")
    with admin.connect() as connection:
        connection.execute(text(f'CREATE DATABASE "{name}"'))
    db_url = make_url(server_url).set(database=name).render_as_string(hide_password=False)
    engine = create_engine(db_url)
    monkeypatch.setenv("DATABASE_URL", db_url)
    _clear_caches()
    config = Config(str(PROJECT_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(PROJECT_ROOT / "migrations"))
    try:
        yield engine, config
    finally:
        engine.dispose()
        _clear_caches()
        with admin.connect() as connection:
            connection.execute(text(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)'))
        admin.dispose()


def _public_tables(engine: Engine) -> set[str]:
    with engine.connect() as connection:
        rows = connection.execute(
            text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
        )
        return {row[0] for row in rows}


def _alembic_version(engine: Engine) -> str:
    with engine.connect() as connection:
        return connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()


def test_upgrade_creates_schema_on_fresh_database(scratch_db: tuple[Engine, Config]) -> None:
    engine, config = scratch_db
    command.upgrade(config, "head")
    assert _public_tables(engine) == FOCUS_TODO_TABLES | {"alembic_version"}
    assert _alembic_version(engine) == "0001_focus_todo_baseline"


def test_upgrade_adopts_preloaded_schema_repeatedly(scratch_db: tuple[Engine, Config]) -> None:
    engine, config = scratch_db
    with engine.begin() as connection:
        connection.exec_driver_sql(SCHEMA_SQL.read_text())
        connection.execute(text("INSERT INTO projects (id, name) VALUES ('P1', 'Imported')"))
        connection.execute(
            text("INSERT INTO tasks (id, project_id, name) VALUES ('T1', 'P1', 'Imported')")
        )
        connection.execute(
            text(
                "INSERT INTO pomodoro_sessions (id, task_id, interval_seconds) "
                "VALUES ('ABC-UPPER', 'T1', 1500)"
            )
        )

    command.upgrade(config, "head")
    command.upgrade(config, "head")

    assert _public_tables(engine) == FOCUS_TODO_TABLES | {"alembic_version"}
    assert _alembic_version(engine) == "0001_focus_todo_baseline"
    with engine.connect() as connection:
        ids = connection.execute(text("SELECT id FROM pomodoro_sessions")).scalars().all()
    assert ids == ["ABC-UPPER"]


_SQL_TYPES = {
    Text: "text",
    Integer: "integer",
    SmallInteger: "smallint",
    Boolean: "boolean",
    DateTime: "timestamp with time zone",
}


def _orm_type_name(column_type: object) -> str:
    for python_type, sql_name in _SQL_TYPES.items():
        if type(column_type) is python_type:
            if isinstance(column_type, DateTime):
                assert column_type.timezone, "timestamps must be timezone-aware"
            return sql_name
    raise AssertionError(f"unmapped ORM type {column_type!r}")


def test_orm_columns_match_database(scratch_db: tuple[Engine, Config]) -> None:
    engine, config = scratch_db
    command.upgrade(config, "head")
    assert set(Base.metadata.tables) == FOCUS_TODO_TABLES

    with engine.connect() as connection:
        for table_name, table in Base.metadata.tables.items():
            rows = connection.execute(
                text(
                    "SELECT column_name, data_type, is_nullable "
                    "FROM information_schema.columns "
                    "WHERE table_schema = 'public' AND table_name = :table "
                    "ORDER BY ordinal_position"
                ),
                {"table": table_name},
            ).all()
            database_columns = [(name, data_type, nullable == "YES") for name, data_type, nullable in rows]
            orm_columns = [
                (column.name, _orm_type_name(column.type), bool(column.nullable))
                for column in table.columns
            ]
            assert orm_columns == database_columns, table_name

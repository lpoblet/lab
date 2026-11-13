import os
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine.url import make_url

from app.config import get_settings, normalize_database_url
from app.db.engine import get_engine, get_session_factory
from app.factory import create_app

DEFAULT_TEST_DATABASE_URL = "postgresql://postgres:review@127.0.0.1:55432/postgres"
TEST_SESSION_TIMEZONE = "America/New_York"
PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _clear_caches() -> None:
    get_settings.cache_clear()
    get_engine.cache_clear()
    get_session_factory.cache_clear()


def _with_non_utc_session_timezone(url: str) -> str:
    parsed = make_url(normalize_database_url(url))
    timezone_option = f"-c timezone={TEST_SESSION_TIMEZONE}"
    existing = parsed.query.get("options", "")
    options = f"{existing} {timezone_option}".strip() if existing else timezone_option
    return parsed.update_query_dict({"options": options}).render_as_string(hide_password=False)


def _test_database_url() -> str:
    return _with_non_utc_session_timezone(
        os.environ.get("TEST_DATABASE_URL", DEFAULT_TEST_DATABASE_URL)
    )


def _postgres_reachable(url: str) -> bool:
    engine = create_engine(
        normalize_database_url(url),
        connect_args={"connect_timeout": 2},
        pool_pre_ping=False,
    )
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
    finally:
        engine.dispose()


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    url = _test_database_url()
    if not _postgres_reachable(url):
        pytest.skip(
            f"Postgres not reachable at {url}. Start throwaway postgres:15 on "
            "127.0.0.1:55432 or set TEST_DATABASE_URL."
        )
    monkeypatch.setenv("DATABASE_URL", url)
    monkeypatch.setenv("DB_CONNECT_TIMEOUT", "3")
    _clear_caches()
    _upgrade_to_head()
    with TestClient(create_app()) as test_client:
        yield test_client
    _clear_caches()


def _upgrade_to_head() -> None:
    """Apply the idempotent baseline so a fresh throwaway database has the schema."""
    config = Config(str(PROJECT_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(PROJECT_ROOT / "migrations"))
    command.upgrade(config, "head")
    get_settings.cache_clear()


@dataclass(frozen=True)
class Catalog:
    project_id: str
    other_project_id: str
    deleted_project_id: str
    task_id: str
    task_name: str
    other_task_id: str
    deleted_task_id: str
    subtask_id: str
    other_subtask_id: str
    deleted_subtask_id: str
    task_ids: tuple[str, ...]


@pytest.fixture
def catalog(client: TestClient) -> Iterator[Catalog]:
    """Seed uniquely named Focus To-Do rows and remove them, with their sessions, afterwards."""
    tag = uuid4().hex[:8].upper()
    seeded = Catalog(
        project_id=f"P-{tag}",
        other_project_id=f"P2-{tag}",
        deleted_project_id=f"PX-{tag}",
        task_id=f"T-{tag}",
        task_name=f"Deep work {tag}",
        other_task_id=f"T2-{tag}",
        deleted_task_id=f"TX-{tag}",
        subtask_id=f"S-{tag}",
        other_subtask_id=f"S2-{tag}",
        deleted_subtask_id=f"SX-{tag}",
        task_ids=(f"T-{tag}", f"T2-{tag}", f"TX-{tag}"),
    )
    projects = [
        {"id": seeded.project_id, "name": f"Work {tag}", "state": 0},
        {"id": seeded.other_project_id, "name": f"Home {tag}", "state": 0},
        {"id": seeded.deleted_project_id, "name": f"Gone {tag}", "state": -1},
    ]
    tasks = [
        {"id": seeded.task_id, "project_id": seeded.project_id,
         "name": seeded.task_name, "interval": 1500, "state": 0},
        {"id": seeded.other_task_id, "project_id": seeded.other_project_id,
         "name": f"Chores {tag}", "interval": 900, "state": 0},
        {"id": seeded.deleted_task_id, "project_id": seeded.project_id,
         "name": f"Dropped {tag}", "interval": 1500, "state": -1},
    ]
    subtasks = [
        {"id": seeded.subtask_id, "task_id": seeded.task_id, "state": 0},
        {"id": seeded.other_subtask_id, "task_id": seeded.other_task_id, "state": 0},
        {"id": seeded.deleted_subtask_id, "task_id": seeded.task_id, "state": -1},
    ]
    engine = get_engine()
    with engine.begin() as connection:
        connection.execute(
            text("INSERT INTO projects (id, name, state) VALUES (:id, :name, :state)"), projects
        )
        connection.execute(
            text(
                "INSERT INTO tasks (id, project_id, name, pomodoro_interval, state) "
                "VALUES (:id, :project_id, :name, :interval, :state)"
            ),
            tasks,
        )
        connection.execute(
            text(
                "INSERT INTO subtasks (id, task_id, name, state) "
                "VALUES (:id, :task_id, 'step', :state)"
            ),
            subtasks,
        )
    try:
        yield seeded
    finally:
        ids = {"tasks": list(seeded.task_ids)}
        project_ids = {"projects": [p["id"] for p in projects]}
        with engine.begin() as connection:
            connection.execute(
                text("DELETE FROM pomodoro_sessions WHERE task_id = ANY(:tasks)"), ids
            )
            connection.execute(text("DELETE FROM subtasks WHERE task_id = ANY(:tasks)"), ids)
            connection.execute(text("DELETE FROM tasks WHERE id = ANY(:tasks)"), ids)
            connection.execute(text("DELETE FROM projects WHERE id = ANY(:projects)"), project_ids)

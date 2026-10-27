import os
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine.url import make_url

from app.config import get_settings, normalize_database_url
from app.db.engine import get_engine, get_session_factory
from app.factory import create_app

DEFAULT_TEST_DATABASE_URL = "postgresql://postgres:review@127.0.0.1:55432/postgres"
TEST_SESSION_TIMEZONE = "America/New_York"


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
    with TestClient(create_app()) as test_client:
        yield test_client
    _clear_caches()

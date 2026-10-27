from fastapi.testclient import TestClient

from app.config import get_settings
from app.db.engine import get_engine, get_session_factory
from app.factory import create_app


def test_health_ok_without_database() -> None:
    client = TestClient(create_app())
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_ready_503_when_database_unreachable(monkeypatch) -> None:
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql://u:p@127.0.0.1:1/x",
    )
    monkeypatch.setenv("DB_CONNECT_TIMEOUT", "1")
    get_settings.cache_clear()
    get_engine.cache_clear()
    get_session_factory.cache_clear()
    try:
        client = TestClient(create_app())
        response = client.get("/ready")
        assert response.status_code == 503
        assert response.json() == {"status": "unavailable"}
    finally:
        get_settings.cache_clear()
        get_engine.cache_clear()
        get_session_factory.cache_clear()

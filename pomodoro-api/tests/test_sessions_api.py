from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import text

from app.db.engine import get_engine


def _create(client: TestClient, **overrides) -> dict:
    body = {
        "kind": "focus",
        "duration_minutes": 25,
        "label": "work",
    }
    body.update(overrides)
    response = client.post("/sessions", json=body)
    assert response.status_code == 201, response.text
    return response.json()


def test_create_session_returns_running(client: TestClient) -> None:
    payload = _create(client, kind="short_break", duration_minutes=5, label=None)
    assert payload["kind"] == "short_break"
    assert payload["status"] == "running"
    assert payload["ended_at"] is None
    assert payload["duration_minutes"] == 5
    assert payload["label"] is None


def test_complete_and_interrupt_lifecycle(client: TestClient) -> None:
    created = _create(client)
    session_id = created["id"]
    completed = client.post(f"/sessions/{session_id}/complete")
    assert completed.status_code == 200
    body = completed.json()
    assert body["status"] == "completed"
    assert body["ended_at"] is not None

    conflict = client.post(f"/sessions/{session_id}/interrupt")
    assert conflict.status_code == 409

    other = _create(client, label="later")
    interrupted = client.post(f"/sessions/{other['id']}/interrupt")
    assert interrupted.status_code == 200
    assert interrupted.json()["status"] == "interrupted"

    again = client.post(f"/sessions/{other['id']}/complete")
    assert again.status_code == 409


def test_missing_session_is_404(client: TestClient) -> None:
    missing = uuid4()
    complete = client.post(f"/sessions/{missing}/complete")
    assert complete.status_code == 404
    interrupt = client.post(f"/sessions/{missing}/interrupt")
    assert interrupt.status_code == 404


def test_malformed_uuid_path_is_422(client: TestClient) -> None:
    response = client.post("/sessions/not-a-uuid/complete")
    assert response.status_code == 422


def test_invalid_kind_and_duration_are_422(client: TestClient) -> None:
    bad_kind = client.post("/sessions", json={"kind": "nap", "duration_minutes": 25})
    assert bad_kind.status_code == 422
    bad_duration = client.post("/sessions", json={"kind": "focus", "duration_minutes": 0})
    assert bad_duration.status_code == 422
    huge = client.post("/sessions", json={"kind": "focus", "duration_minutes": 10_000_000_000})
    assert huge.status_code == 422
    boolean = client.post("/sessions", json={"kind": "focus", "duration_minutes": True})
    assert boolean.status_code == 422
    as_string = client.post("/sessions", json={"kind": "focus", "duration_minutes": "25"})
    assert as_string.status_code == 422
    as_float = client.post("/sessions", json={"kind": "focus", "duration_minutes": 25.0})
    assert as_float.status_code == 422
    nul_label = client.post(
        "/sessions",
        json={"kind": "focus", "duration_minutes": 25, "label": "a\u0000b"},
    )
    assert nul_label.status_code == 422


def test_list_and_from_to_filter(client: TestClient) -> None:
    first = _create(client, label="first")
    second = _create(client, label="second")
    listed = client.get("/sessions")
    assert listed.status_code == 200
    ids = [row["id"] for row in listed.json()]
    assert second["id"] in ids
    assert first["id"] in ids
    assert ids.index(second["id"]) < ids.index(first["id"])

    started = datetime.fromisoformat(first["started_at"])
    window_from = (started - timedelta(seconds=1)).astimezone(timezone.utc).isoformat()
    window_to = (started + timedelta(hours=1)).astimezone(timezone.utc).isoformat()
    filtered = client.get("/sessions", params={"from": window_from, "to": window_to})
    assert filtered.status_code == 200
    filtered_ids = {row["id"] for row in filtered.json()}
    assert first["id"] in filtered_ids
    assert second["id"] in filtered_ids

    past = (started - timedelta(days=365)).isoformat()
    empty = client.get("/sessions", params={"to": past})
    assert empty.status_code == 200
    assert first["id"] not in {row["id"] for row in empty.json()}


def test_naive_from_to_are_read_as_utc_under_non_utc_session_timezone(client: TestClient) -> None:
    with get_engine().connect() as connection:
        session_timezone = connection.execute(text("SHOW TIME ZONE")).scalar_one()
    assert session_timezone == "America/New_York"

    created = _create(client, label="naive")
    started = datetime.fromisoformat(created["started_at"]).astimezone(timezone.utc)

    naive_from = started.replace(tzinfo=None).isoformat()
    from_only = client.get("/sessions", params={"from": naive_from})
    assert from_only.status_code == 200
    assert created["id"] in {row["id"] for row in from_only.json()}

    naive_to_before = (started - timedelta(hours=1)).replace(tzinfo=None).isoformat()
    to_before = client.get("/sessions", params={"to": naive_to_before})
    assert to_before.status_code == 200
    assert created["id"] not in {row["id"] for row in to_before.json()}


def test_malformed_from_to_are_422(client: TestClient) -> None:
    bad_from = client.get("/sessions", params={"from": "yesterday"})
    assert bad_from.status_code == 422
    bad_to = client.get("/sessions", params={"to": "not-a-date"})
    assert bad_to.status_code == 422

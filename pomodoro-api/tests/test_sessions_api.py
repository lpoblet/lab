from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.db.engine import get_engine
from tests.conftest import Catalog


def _create(client: TestClient, task_id: str, **overrides) -> dict:
    body = {"task_id": task_id, "interval_seconds": 1500}
    body.update(overrides)
    response = client.post("/sessions", json=body)
    assert response.status_code == 201, response.text
    return response.json()


def _ids(response) -> list[str]:
    assert response.status_code == 200, response.text
    return [row["id"] for row in response.json()]


def test_create_applies_extension_defaults(client: TestClient, catalog: Catalog) -> None:
    payload = _create(client, catalog.task_id)
    assert payload["id"] == payload["id"].upper()
    assert payload["task_id"] == catalog.task_id
    assert payload["task_name"] == catalog.task_name
    assert payload["subtask_id"] is None
    assert payload["interval_seconds"] == 1500
    assert payload["pomodoro_interval"] == 1500
    assert payload["obj_type"] == "POMODORO"
    assert payload["state"] == 0
    assert payload["sync"] == 0
    assert payload["is_manual"] is False
    assert payload["completed"] is True
    end = datetime.fromisoformat(payload["end_date"])
    assert datetime.fromisoformat(payload["creation_date"]) == end
    assert abs(end - datetime.now(timezone.utc)) < timedelta(minutes=1)
    assert datetime.fromisoformat(payload["started_at"]) == end - timedelta(seconds=1500)


def test_create_with_explicit_fields(client: TestClient, catalog: Catalog) -> None:
    end = datetime(2026, 11, 12, 9, 0, tzinfo=timezone.utc)
    payload = _create(
        client,
        catalog.task_id,
        subtask_id=catalog.subtask_id,
        interval_seconds=600,
        pomodoro_interval=1800,
        end_date=end.isoformat(),
        is_manual=True,
    )
    assert payload["subtask_id"] == catalog.subtask_id
    assert payload["pomodoro_interval"] == 1800
    assert payload["is_manual"] is True
    assert payload["completed"] is False
    assert datetime.fromisoformat(payload["end_date"]) == end
    assert datetime.fromisoformat(payload["started_at"]) == end - timedelta(seconds=600)


def test_naive_end_date_is_utc(client: TestClient, catalog: Catalog) -> None:
    payload = _create(client, catalog.task_id, end_date="2026-11-12T09:00:00")
    assert datetime.fromisoformat(payload["end_date"]) == datetime(
        2026, 11, 12, 9, 0, tzinfo=timezone.utc
    )


def test_unknown_or_deleted_task_is_404(client: TestClient, catalog: Catalog) -> None:
    for task_id in ("NO-SUCH-TASK", catalog.deleted_task_id):
        response = client.post("/sessions", json={"task_id": task_id, "interval_seconds": 60})
        assert response.status_code == 404, task_id


def test_unknown_or_deleted_subtask_is_404(client: TestClient, catalog: Catalog) -> None:
    for subtask_id in ("NO-SUCH-SUBTASK", catalog.deleted_subtask_id):
        response = client.post(
            "/sessions",
            json={"task_id": catalog.task_id, "subtask_id": subtask_id, "interval_seconds": 60},
        )
        assert response.status_code == 404, subtask_id


def test_subtask_of_another_task_is_422(client: TestClient, catalog: Catalog) -> None:
    response = client.post(
        "/sessions",
        json={
            "task_id": catalog.task_id,
            "subtask_id": catalog.other_subtask_id,
            "interval_seconds": 60,
        },
    )
    assert response.status_code == 422


@pytest.mark.parametrize("seconds", [0, 86_401, True, "1500", 1500.0])
def test_invalid_seconds_are_422(client: TestClient, catalog: Catalog, seconds: object) -> None:
    actual = client.post("/sessions", json={"task_id": catalog.task_id, "interval_seconds": seconds})
    assert actual.status_code == 422
    planned = client.post(
        "/sessions",
        json={"task_id": catalog.task_id, "interval_seconds": 60, "pomodoro_interval": seconds},
    )
    assert planned.status_code == 422


def test_invalid_body_fields_are_422(client: TestClient, catalog: Catalog) -> None:
    for body in (
        {"interval_seconds": 60},
        {"task_id": catalog.task_id},
        {"task_id": catalog.task_id, "interval_seconds": 60, "end_date": "yesterday"},
        {"kind": "focus", "duration_minutes": 25},
    ):
        assert client.post("/sessions", json=body).status_code == 422, body


def test_list_filters_and_orders_by_end_date(client: TestClient, catalog: Catalog) -> None:
    base = datetime(2026, 11, 12, 8, 0, tzinfo=timezone.utc)
    older = _create(client, catalog.task_id, end_date=base.isoformat())
    newer = _create(client, catalog.task_id, end_date=(base + timedelta(hours=1)).isoformat())
    other = _create(client, catalog.other_task_id, end_date=(base + timedelta(hours=2)).isoformat())

    by_task = _ids(client.get("/sessions", params={"task_id": catalog.task_id}))
    assert by_task == [newer["id"], older["id"]]

    window = client.get(
        "/sessions",
        params={
            "from": (base + timedelta(minutes=30)).isoformat(),
            "to": (base + timedelta(hours=3)).isoformat(),
        },
    )
    window_ids = _ids(window)
    assert older["id"] not in window_ids
    assert window_ids.index(other["id"]) < window_ids.index(newer["id"])

    rows = {row["id"]: row for row in window.json()}
    assert rows[newer["id"]]["task_name"] == catalog.task_name


def test_list_from_filters_on_end_date_not_start(client: TestClient, catalog: Catalog) -> None:
    end = datetime(2026, 11, 12, 8, 0, tzinfo=timezone.utc)
    created = _create(client, catalog.task_id, interval_seconds=1500, end_date=end.isoformat())
    # The block started before `from` but ended after it, so it is included.
    just_before_end = (end - timedelta(minutes=1)).isoformat()
    assert created["id"] in _ids(client.get("/sessions", params={"from": just_before_end}))


def test_naive_from_to_are_read_as_utc_under_non_utc_session_timezone(
    client: TestClient, catalog: Catalog
) -> None:
    with get_engine().connect() as connection:
        session_timezone = connection.execute(text("SHOW TIME ZONE")).scalar_one()
    assert session_timezone == "America/New_York"

    end = datetime(2026, 11, 12, 15, 0, tzinfo=timezone.utc)
    created = _create(client, catalog.task_id, end_date=end.isoformat())

    naive_from = end.replace(tzinfo=None).isoformat()
    assert created["id"] in _ids(client.get("/sessions", params={"from": naive_from}))

    naive_to_before = (end - timedelta(hours=1)).replace(tzinfo=None).isoformat()
    assert created["id"] not in _ids(client.get("/sessions", params={"to": naive_to_before}))


def test_malformed_from_to_are_422(client: TestClient) -> None:
    assert client.get("/sessions", params={"from": "yesterday"}).status_code == 422
    assert client.get("/sessions", params={"to": "not-a-date"}).status_code == 422


def test_get_by_id_matches_text_exactly(client: TestClient, catalog: Catalog) -> None:
    mixed_id = "AbCd-Imported-Session"
    with get_engine().begin() as connection:
        connection.execute(
            text(
                "INSERT INTO pomodoro_sessions (id, task_id, obj_type, interval_seconds, "
                "pomodoro_interval, state, sync, creation_date, end_date) VALUES "
                "(:id, :task, 'POMODORO', 1200, 1500, 0, 1, :end, :end)"
            ),
            {"id": mixed_id, "task": catalog.task_id, "end": datetime(2026, 5, 18, tzinfo=timezone.utc)},
        )
    found = client.get(f"/sessions/{mixed_id}")
    assert found.status_code == 200
    body = found.json()
    assert body["id"] == mixed_id
    assert body["sync"] == 1
    assert body["completed"] is False
    assert client.get(f"/sessions/{mixed_id.lower()}").status_code == 404

    created = _create(client, catalog.task_id)
    assert client.get(f"/sessions/{created['id']}").json()["id"] == created["id"]


def test_missing_session_is_404(client: TestClient) -> None:
    assert client.get("/sessions/does-not-exist").status_code == 404
    assert client.delete("/sessions/does-not-exist").status_code == 404


def test_delete_soft_deletes(client: TestClient, catalog: Catalog) -> None:
    created = _create(client, catalog.task_id)
    session_id = created["id"]

    deleted = client.delete(f"/sessions/{session_id}")
    assert deleted.status_code == 204
    assert deleted.content == b""

    assert client.get(f"/sessions/{session_id}").status_code == 404
    assert session_id not in _ids(client.get("/sessions", params={"task_id": catalog.task_id}))
    assert client.delete(f"/sessions/{session_id}").status_code == 404

    with get_engine().connect() as connection:
        state = connection.execute(
            text("SELECT state FROM pomodoro_sessions WHERE id = :id"), {"id": session_id}
        ).scalar_one()
    assert state == -1

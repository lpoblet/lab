from fastapi.testclient import TestClient

from tests.conftest import Catalog


def test_projects_exclude_deleted(client: TestClient, catalog: Catalog) -> None:
    response = client.get("/projects")
    assert response.status_code == 200
    ids = {row["id"] for row in response.json()}
    assert {catalog.project_id, catalog.other_project_id} <= ids
    assert catalog.deleted_project_id not in ids


def test_tasks_exclude_deleted(client: TestClient, catalog: Catalog) -> None:
    response = client.get("/tasks")
    assert response.status_code == 200
    rows = {row["id"]: row for row in response.json()}
    assert {catalog.task_id, catalog.other_task_id} <= rows.keys()
    assert catalog.deleted_task_id not in rows
    assert rows[catalog.task_id]["name"] == catalog.task_name
    assert rows[catalog.task_id]["pomodoro_interval"] == 1500


def test_tasks_filter_by_project(client: TestClient, catalog: Catalog) -> None:
    response = client.get("/tasks", params={"project_id": catalog.project_id})
    assert response.status_code == 200
    assert [row["id"] for row in response.json()] == [catalog.task_id]

    unknown = client.get("/tasks", params={"project_id": "NO-SUCH-PROJECT"})
    assert unknown.status_code == 200
    assert unknown.json() == []


def test_catalog_is_read_only(client: TestClient) -> None:
    assert client.post("/projects", json={"name": "x"}).status_code == 405
    assert client.post("/tasks", json={"name": "x"}).status_code == 405

from fastapi import APIRouter, Query

from app.db import repository
from app.domain.catalog import Project, Task

router = APIRouter()


@router.get("/projects")
def list_projects() -> list[Project]:
    return repository.list_projects()


@router.get("/tasks")
def list_tasks(project_id: str | None = Query(default=None)) -> list[Task]:
    return repository.list_tasks(project_id=project_id)

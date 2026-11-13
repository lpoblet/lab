"""Read-only views of Focus To-Do projects and tasks (the extension owns writes)."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class Project(BaseModel):
    model_config = ConfigDict(frozen=True, from_attributes=True)

    id: str
    name: str
    parent_id: str | None = None
    color: str | None = None
    is_default: bool = False
    sort_order: int | None = None
    state: int | None = None


class Task(BaseModel):
    model_config = ConfigDict(frozen=True, from_attributes=True)

    id: str
    project_id: str | None = None
    name: str
    priority: int | None = None
    is_finished: bool = False
    estimate_pomo_num: int | None = None
    actual_pomo_num: int | None = None
    pomodoro_interval: int | None = None
    sort_order: int | None = None
    state: int | None = None
    deadline: datetime | None = None

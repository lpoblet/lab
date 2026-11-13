from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import Select, select, update
from sqlalchemy.orm import Session

from app.db.engine import get_session_factory
from app.db.models import PomodoroSessionRow, ProjectRow, SubtaskRow, TaskRow
from app.domain.catalog import Project, Task
from app.domain.session import (
    POMODORO_OBJ_TYPE,
    STATE_ACTIVE,
    STATE_DELETED,
    SYNC_LOCAL,
    NewSession,
    PomodoroSession,
    utcnow,
)


class SessionNotFound(Exception):
    def __init__(self, session_id: str) -> None:
        super().__init__(f"Session {session_id} not found")
        self.session_id = session_id


class TaskNotFound(Exception):
    def __init__(self, task_id: str) -> None:
        super().__init__(f"Task {task_id} not found")
        self.task_id = task_id


class SubtaskNotFound(Exception):
    def __init__(self, subtask_id: str) -> None:
        super().__init__(f"Subtask {subtask_id} not found")
        self.subtask_id = subtask_id


class SubtaskMismatch(Exception):
    def __init__(self, subtask_id: str, task_id: str) -> None:
        super().__init__(f"Subtask {subtask_id} does not belong to task {task_id}")
        self.subtask_id = subtask_id
        self.task_id = task_id


_SESSION_COLUMNS = tuple(column.key for column in PomodoroSessionRow.__table__.columns)


def _not_deleted(state_column: Any) -> Any:
    # The extension soft-deletes with state = -1; NULL states count as live.
    return state_column.is_distinct_from(STATE_DELETED)


def _to_domain(row: PomodoroSessionRow, task_name: str | None) -> PomodoroSession:
    data = {key: getattr(row, key) for key in _SESSION_COLUMNS}
    return PomodoroSession.model_validate({**data, "task_name": task_name})


def _session_stmt() -> Select[tuple[PomodoroSessionRow, str | None]]:
    return (
        select(PomodoroSessionRow, TaskRow.name)
        .outerjoin(TaskRow, TaskRow.id == PomodoroSessionRow.task_id)
        .where(_not_deleted(PomodoroSessionRow.state))
    )


def _live_task(db: Session, task_id: str) -> TaskRow:
    task = db.get(TaskRow, task_id)
    if task is None or task.state == STATE_DELETED:
        raise TaskNotFound(task_id)
    return task


def _check_subtask(db: Session, subtask_id: str, task_id: str) -> None:
    subtask = db.get(SubtaskRow, subtask_id)
    if subtask is None or subtask.state == STATE_DELETED:
        raise SubtaskNotFound(subtask_id)
    if subtask.task_id != task_id:
        raise SubtaskMismatch(subtask_id, task_id)


def create_session(new: NewSession) -> PomodoroSession:
    end_date = new.end_date or utcnow()
    factory = get_session_factory()
    with factory() as db:
        with db.begin():
            task = _live_task(db, new.task_id)
            if new.subtask_id is not None:
                _check_subtask(db, new.subtask_id, new.task_id)
            row = PomodoroSessionRow(
                # Upper-case uuid4 text is the extension's dominant id format.
                id=str(uuid4()).upper(),
                task_id=task.id,
                subtask_id=new.subtask_id,
                obj_type=POMODORO_OBJ_TYPE,
                interval_seconds=new.interval_seconds,
                pomodoro_interval=(
                    new.pomodoro_interval
                    if new.pomodoro_interval is not None
                    else task.pomodoro_interval
                ),
                is_manual=new.is_manual,
                state=STATE_ACTIVE,
                sync=SYNC_LOCAL,
                # The extension writes creation_date equal to end_date.
                creation_date=end_date,
                end_date=end_date,
            )
            db.add(row)
            task_name = task.name
        db.refresh(row)
        return _to_domain(row, task_name)


def get_session(session_id: str) -> PomodoroSession:
    factory = get_session_factory()
    with factory() as db:
        result = db.execute(_session_stmt().where(PomodoroSessionRow.id == session_id)).first()
        if result is None:
            raise SessionNotFound(session_id)
        row, task_name = result
        return _to_domain(row, task_name)


def list_sessions(
    from_ts: datetime | None = None,
    to_ts: datetime | None = None,
    task_id: str | None = None,
) -> list[PomodoroSession]:
    stmt = _session_stmt()
    if from_ts is not None:
        stmt = stmt.where(PomodoroSessionRow.end_date >= from_ts)
    if to_ts is not None:
        stmt = stmt.where(PomodoroSessionRow.end_date <= to_ts)
    if task_id is not None:
        stmt = stmt.where(PomodoroSessionRow.task_id == task_id)
    stmt = stmt.order_by(
        PomodoroSessionRow.end_date.desc().nulls_last(), PomodoroSessionRow.id.desc()
    )
    factory = get_session_factory()
    with factory() as db:
        return [_to_domain(row, task_name) for row, task_name in db.execute(stmt).all()]


def soft_delete_session(session_id: str) -> None:
    """Mark a session deleted (state = -1) in one conditional UPDATE.

    The state check in the WHERE clause makes concurrent deletes race-free: only
    one caller sees rowcount 1, every other one gets SessionNotFound.
    """
    factory = get_session_factory()
    with factory() as db:
        with db.begin():
            result = db.execute(
                update(PomodoroSessionRow)
                .where(
                    PomodoroSessionRow.id == session_id,
                    _not_deleted(PomodoroSessionRow.state),
                )
                .values(state=STATE_DELETED)
            )
            if result.rowcount != 1:
                raise SessionNotFound(session_id)


def list_projects() -> list[Project]:
    stmt = (
        select(ProjectRow)
        .where(_not_deleted(ProjectRow.state))
        .order_by(ProjectRow.sort_order.asc().nulls_last(), ProjectRow.name, ProjectRow.id)
    )
    factory = get_session_factory()
    with factory() as db:
        return [Project.model_validate(row) for row in db.scalars(stmt).all()]


def list_tasks(project_id: str | None = None) -> list[Task]:
    stmt = select(TaskRow).where(_not_deleted(TaskRow.state))
    if project_id is not None:
        stmt = stmt.where(TaskRow.project_id == project_id)
    stmt = stmt.order_by(TaskRow.sort_order.asc().nulls_last(), TaskRow.name, TaskRow.id)
    factory = get_session_factory()
    with factory() as db:
        return [Task.model_validate(row) for row in db.scalars(stmt).all()]

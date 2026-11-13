from datetime import datetime

from fastapi import APIRouter, Query, Response

from app.db import repository
from app.domain.session import NewSession, PomodoroSession, _ensure_aware

router = APIRouter()


@router.post("/sessions", status_code=201)
def record_session(body: NewSession) -> PomodoroSession:
    return repository.create_session(body)


@router.get("/sessions")
def list_sessions(
    from_: datetime | None = Query(default=None, alias="from"),
    to: datetime | None = Query(default=None),
    task_id: str | None = Query(default=None),
) -> list[PomodoroSession]:
    from_ts = _ensure_aware(from_) if from_ is not None else None
    to_ts = _ensure_aware(to) if to is not None else None
    return repository.list_sessions(from_ts=from_ts, to_ts=to_ts, task_id=task_id)


@router.get("/sessions/{session_id}")
def get_session(session_id: str) -> PomodoroSession:
    return repository.get_session(session_id)


@router.delete("/sessions/{session_id}", status_code=204)
def delete_session(session_id: str) -> Response:
    repository.soft_delete_session(session_id)
    return Response(status_code=204)

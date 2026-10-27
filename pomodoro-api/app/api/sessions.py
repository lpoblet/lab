from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field, field_validator

from app.db import repository
from app.domain.session import PomodoroSession, SessionKind, _ensure_aware

router = APIRouter()

_MAX_DURATION_MINUTES = 1440
_MAX_LABEL_LENGTH = 256


class CreateSessionRequest(BaseModel):
    kind: SessionKind
    duration_minutes: int = Field(gt=0, le=_MAX_DURATION_MINUTES, strict=True)
    label: str | None = Field(default=None, max_length=_MAX_LABEL_LENGTH)

    @field_validator("label")
    @classmethod
    def _label_printable(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if "\x00" in value or any(ord(ch) < 32 and ch not in "\t\n\r" for ch in value):
            raise ValueError("label must not contain NUL or control characters")
        return value


@router.post("/sessions", status_code=201)
def start_session(body: CreateSessionRequest) -> PomodoroSession:
    session = PomodoroSession(
        kind=body.kind,
        duration_minutes=body.duration_minutes,
        label=body.label,
    )
    return repository.create_session(session)


@router.get("/sessions")
def list_sessions(
    from_: datetime | None = Query(default=None, alias="from"),
    to: datetime | None = Query(default=None),
) -> list[PomodoroSession]:
    from_ts = _ensure_aware(from_) if from_ is not None else None
    to_ts = _ensure_aware(to) if to is not None else None
    return repository.list_sessions(from_ts=from_ts, to_ts=to_ts)


@router.post("/sessions/{session_id}/complete")
def complete_session(session_id: UUID) -> PomodoroSession:
    return repository.complete(session_id)


@router.post("/sessions/{session_id}/interrupt")
def interrupt_session(session_id: UUID) -> PomodoroSession:
    return repository.interrupt(session_id)

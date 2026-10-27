from datetime import datetime, timezone
from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class SessionKind(StrEnum):
    FOCUS = "focus"
    SHORT_BREAK = "short_break"
    LONG_BREAK = "long_break"


class SessionStatus(StrEnum):
    RUNNING = "running"
    COMPLETED = "completed"
    INTERRUPTED = "interrupted"


class InvalidSessionTransition(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _ensure_aware(ts: datetime) -> datetime:
    if ts.tzinfo is None:
        return ts.replace(tzinfo=timezone.utc)
    return ts


class PomodoroSession(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: UUID = Field(default_factory=uuid4)
    kind: SessionKind
    status: SessionStatus = SessionStatus.RUNNING
    duration_minutes: int = Field(gt=0, le=1440, strict=True)
    label: str | None = Field(default=None, max_length=256)
    started_at: datetime = Field(default_factory=utcnow)
    ended_at: datetime | None = None

    @field_validator("started_at", "ended_at", mode="after")
    @classmethod
    def _timestamps_aware(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        return _ensure_aware(value)

    @model_validator(mode="after")
    def _status_matches_ended_at(self) -> "PomodoroSession":
        if self.status == SessionStatus.RUNNING:
            if self.ended_at is not None:
                raise ValueError("running sessions must have ended_at unset")
        elif self.ended_at is None:
            raise ValueError(f"{self.status.value} sessions must have ended_at set")
        elif self.ended_at < self.started_at:
            raise ValueError("ended_at must not be before started_at")
        return self


def _require_running(session: PomodoroSession, action: str) -> None:
    if session.status != SessionStatus.RUNNING:
        raise InvalidSessionTransition(
            f"Cannot {action} session {session.id} with status {session.status.value}"
        )


def _ended_copy(
    session: PomodoroSession,
    action: str,
    status: SessionStatus,
    ended_at: datetime | None,
) -> PomodoroSession:
    _require_running(session, action)
    end = _ensure_aware(ended_at or utcnow())
    start = _ensure_aware(session.started_at)
    if end < start:
        raise InvalidSessionTransition(
            f"Cannot {action} session {session.id}: ended_at is before started_at"
        )
    return PomodoroSession.model_validate(
        {**session.model_dump(), "status": status, "ended_at": end}
    )


def complete_session(session: PomodoroSession, ended_at: datetime | None = None) -> PomodoroSession:
    return _ended_copy(session, "complete", SessionStatus.COMPLETED, ended_at)


def interrupt_session(session: PomodoroSession, ended_at: datetime | None = None) -> PomodoroSession:
    return _ended_copy(session, "interrupt", SessionStatus.INTERRUPTED, ended_at)

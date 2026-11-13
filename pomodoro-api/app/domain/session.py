"""Finished focus blocks, modelled the way the Focus To-Do extension stores them.

The extension only writes a row once a pomodoro ends: ``end_date`` is the end
time, ``interval_seconds`` the actual focused time and ``pomodoro_interval`` the
planned length. The start time is never stored, so it is derived.
"""
from datetime import datetime, timedelta, timezone

from pydantic import BaseModel, ConfigDict, Field, StrictBool, computed_field, field_validator

MAX_SECONDS = 86_400
MAX_ID_LENGTH = 64
POMODORO_OBJ_TYPE = "POMODORO"
STATE_ACTIVE = 0
STATE_DELETED = -1
# Rows written by the API were never synced to the Focus To-Do cloud; imports carry 1.
SYNC_LOCAL = 0


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _ensure_aware(ts: datetime) -> datetime:
    if ts.tzinfo is None:
        return ts.replace(tzinfo=timezone.utc)
    return ts


class NewSession(BaseModel):
    """Body of ``POST /sessions``: a pomodoro that has already finished."""

    model_config = ConfigDict(extra="forbid")

    task_id: str = Field(min_length=1, max_length=MAX_ID_LENGTH)
    subtask_id: str | None = Field(default=None, min_length=1, max_length=MAX_ID_LENGTH)
    interval_seconds: int = Field(gt=0, le=MAX_SECONDS, strict=True)
    pomodoro_interval: int | None = Field(default=None, gt=0, le=MAX_SECONDS, strict=True)
    end_date: datetime | None = None
    is_manual: StrictBool = False

    @field_validator("end_date", mode="after")
    @classmethod
    def _end_date_aware(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        return _ensure_aware(value)


class PomodoroSession(BaseModel):
    """A stored ``pomodoro_sessions`` row plus the linked task name.

    Columns are nullable in the export schema, so imported rows may lack
    values; derived fields then fall back to ``None``.
    """

    model_config = ConfigDict(frozen=True)

    id: str
    task_id: str | None = None
    task_name: str | None = None
    subtask_id: str | None = None
    obj_type: str | None = None
    interval_seconds: int | None = None
    pomodoro_interval: int | None = None
    is_manual: bool = False
    state: int | None = None
    sync: int | None = None
    creation_date: datetime | None = None
    end_date: datetime | None = None

    @field_validator("creation_date", "end_date", mode="after")
    @classmethod
    def _timestamps_aware(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        return _ensure_aware(value)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def started_at(self) -> datetime | None:
        if self.end_date is None or self.interval_seconds is None:
            return None
        return self.end_date - timedelta(seconds=self.interval_seconds)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def completed(self) -> bool:
        """True when the focused time reached the planned interval."""
        if self.interval_seconds is None:
            return False
        if self.pomodoro_interval is None:
            return True
        return self.interval_seconds >= self.pomodoro_interval

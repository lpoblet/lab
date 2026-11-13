from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from app.domain.session import MAX_SECONDS, NewSession, PomodoroSession


def _stored(**overrides) -> PomodoroSession:
    data = {
        "id": "ABCDEF12-3456-7890-ABCD-EF1234567890",
        "task_id": "T1",
        "interval_seconds": 1500,
        "pomodoro_interval": 1500,
        "end_date": datetime(2026, 11, 12, 10, 25, tzinfo=timezone.utc),
    }
    data.update(overrides)
    return PomodoroSession(**data)


def test_started_at_is_end_date_minus_interval() -> None:
    session = _stored(interval_seconds=600)
    assert session.started_at == datetime(2026, 11, 12, 10, 15, tzinfo=timezone.utc)


def test_started_at_is_none_without_end_date() -> None:
    assert _stored(end_date=None).started_at is None


def test_completed_reflects_planned_interval() -> None:
    assert _stored(interval_seconds=1500, pomodoro_interval=1500).completed is True
    assert _stored(interval_seconds=1499, pomodoro_interval=1500).completed is False
    assert _stored(pomodoro_interval=None).completed is True
    assert _stored(interval_seconds=None).completed is False


def test_session_is_frozen_and_keeps_id_case() -> None:
    session = _stored(id="MixedCase-Id")
    assert session.id == "MixedCase-Id"
    with pytest.raises(ValidationError):
        session.state = -1  # type: ignore[misc]


def test_naive_timestamps_are_utc() -> None:
    naive = datetime(2026, 11, 12, 10, 25)
    assert _stored(end_date=naive).end_date == naive.replace(tzinfo=timezone.utc)
    assert NewSession(task_id="T1", interval_seconds=1, end_date=naive).end_date.tzinfo is not None


def test_computed_fields_are_serialized() -> None:
    dumped = _stored().model_dump()
    assert dumped["started_at"] == dumped["end_date"] - timedelta(seconds=1500)
    assert dumped["completed"] is True


def test_new_session_defaults() -> None:
    new = NewSession(task_id="T1", interval_seconds=1500)
    assert new.pomodoro_interval is None
    assert new.subtask_id is None
    assert new.end_date is None
    assert new.is_manual is False


@pytest.mark.parametrize("seconds", [0, -1, MAX_SECONDS + 1, True, "1500", 1500.0])
def test_new_session_rejects_bad_seconds(seconds: object) -> None:
    with pytest.raises(ValidationError):
        NewSession(task_id="T1", interval_seconds=seconds)
    with pytest.raises(ValidationError):
        NewSession(task_id="T1", interval_seconds=1, pomodoro_interval=seconds)


def test_new_session_accepts_bounds() -> None:
    assert NewSession(task_id="T1", interval_seconds=1).interval_seconds == 1
    assert NewSession(task_id="T1", interval_seconds=MAX_SECONDS).interval_seconds == MAX_SECONDS


@pytest.mark.parametrize(
    "overrides",
    [
        {"task_id": ""},
        {"task_id": "x" * 65},
        {"subtask_id": ""},
        {"end_date": "not-a-date"},
        {"is_manual": "yes"},
        {"kind": "focus"},
    ],
)
def test_new_session_rejects_bad_fields(overrides: dict) -> None:
    with pytest.raises(ValidationError):
        NewSession(**{"task_id": "T1", "interval_seconds": 1500, **overrides})

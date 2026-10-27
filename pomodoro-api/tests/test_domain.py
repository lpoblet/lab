from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from app.domain.session import (
    InvalidSessionTransition,
    PomodoroSession,
    SessionKind,
    SessionStatus,
    complete_session,
    interrupt_session,
    utcnow,
)


def _running(**overrides) -> PomodoroSession:
    data = {
        "kind": SessionKind.FOCUS,
        "duration_minutes": 25,
        "label": "deep work",
    }
    data.update(overrides)
    return PomodoroSession(**data)


def test_new_session_is_running_with_null_ended_at() -> None:
    session = _running()
    assert session.status is SessionStatus.RUNNING
    assert session.ended_at is None


def test_complete_running_sets_status_and_ended_at() -> None:
    session = _running()
    ended = session.started_at + timedelta(minutes=25)
    completed = complete_session(session, ended_at=ended)
    assert completed.status is SessionStatus.COMPLETED
    assert completed.ended_at == ended
    assert completed.id == session.id


def test_interrupt_running_sets_status_and_ended_at() -> None:
    session = _running()
    interrupted = interrupt_session(session)
    assert interrupted.status is SessionStatus.INTERRUPTED
    assert interrupted.ended_at is not None
    assert interrupted.ended_at >= session.started_at


def test_complete_non_running_raises() -> None:
    session = complete_session(_running())
    with pytest.raises(InvalidSessionTransition):
        complete_session(session)


def test_interrupt_completed_raises() -> None:
    session = complete_session(_running())
    with pytest.raises(InvalidSessionTransition):
        interrupt_session(session)


def test_complete_ended_before_started_raises() -> None:
    started = utcnow()
    session = _running(started_at=started)
    with pytest.raises(InvalidSessionTransition):
        complete_session(session, ended_at=started - timedelta(seconds=1))


def test_running_with_ended_at_rejected() -> None:
    with pytest.raises(ValueError):
        PomodoroSession(
            id=uuid4(),
            kind=SessionKind.FOCUS,
            status=SessionStatus.RUNNING,
            duration_minutes=25,
            started_at=utcnow(),
            ended_at=utcnow(),
        )


def test_naive_timestamps_are_made_aware() -> None:
    naive = datetime(2026, 1, 1, 12, 0, 0)
    session = _running(started_at=naive)
    assert session.started_at.tzinfo == timezone.utc

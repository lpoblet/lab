from datetime import datetime
from uuid import UUID

from sqlalchemy import Select, select, update

from app.db.engine import get_session_factory
from app.db.models import PomodoroSessionRow
from app.domain.session import (
    InvalidSessionTransition,
    PomodoroSession,
    SessionStatus,
    utcnow,
)


class SessionNotFound(Exception):
    def __init__(self, session_id: UUID) -> None:
        super().__init__(f"Session {session_id} not found")
        self.session_id = session_id


def _to_domain(row: PomodoroSessionRow) -> PomodoroSession:
    return PomodoroSession.model_validate(row, from_attributes=True)


def _list_stmt(from_ts: datetime | None, to_ts: datetime | None) -> Select[tuple[PomodoroSessionRow]]:
    stmt = select(PomodoroSessionRow)
    if from_ts is not None:
        stmt = stmt.where(PomodoroSessionRow.started_at >= from_ts)
    if to_ts is not None:
        stmt = stmt.where(PomodoroSessionRow.started_at <= to_ts)
    return stmt.order_by(PomodoroSessionRow.started_at.desc(), PomodoroSessionRow.id.desc())


def create_session(session: PomodoroSession) -> PomodoroSession:
    row = PomodoroSessionRow(
        id=session.id,
        kind=session.kind,
        status=session.status,
        duration_minutes=session.duration_minutes,
        label=session.label,
        started_at=session.started_at,
        ended_at=session.ended_at,
    )
    factory = get_session_factory()
    with factory() as db:
        with db.begin():
            db.add(row)
        db.refresh(row)
        return _to_domain(row)


def get_session(session_id: UUID) -> PomodoroSession:
    factory = get_session_factory()
    with factory() as db:
        row = db.get(PomodoroSessionRow, session_id)
        if row is None:
            raise SessionNotFound(session_id)
        return _to_domain(row)


def list_sessions(from_ts: datetime | None = None, to_ts: datetime | None = None) -> list[PomodoroSession]:
    factory = get_session_factory()
    with factory() as db:
        rows = db.scalars(_list_stmt(from_ts, to_ts)).all()
        return [_to_domain(row) for row in rows]


def _end_session(session_id: UUID, action: str, status: SessionStatus) -> PomodoroSession:
    ended_at = utcnow()
    factory = get_session_factory()
    with factory() as db:
        with db.begin():
            result = db.execute(
                update(PomodoroSessionRow)
                .where(
                    PomodoroSessionRow.id == session_id,
                    PomodoroSessionRow.status == SessionStatus.RUNNING,
                )
                .values(status=status, ended_at=ended_at)
            )
            if result.rowcount == 1:
                row = db.get(PomodoroSessionRow, session_id)
                if row is None:
                    raise SessionNotFound(session_id)
                return _to_domain(row)

            row = db.get(PomodoroSessionRow, session_id)
            if row is None:
                raise SessionNotFound(session_id)
            raise InvalidSessionTransition(
                f"Cannot {action} session {session_id} with status {row.status}"
            )


def complete(session_id: UUID) -> PomodoroSession:
    return _end_session(session_id, "complete", SessionStatus.COMPLETED)


def interrupt(session_id: UUID) -> PomodoroSession:
    return _end_session(session_id, "interrupt", SessionStatus.INTERRUPTED)

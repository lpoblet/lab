from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.domain.session import SessionKind, SessionStatus


class Base(DeclarativeBase):
    pass


class PomodoroSessionRow(Base):
    __tablename__ = "pomodoro_sessions"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    kind: Mapped[SessionKind] = mapped_column(String(32), nullable=False)
    status: Mapped[SessionStatus] = mapped_column(String(32), nullable=False)
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    label: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

"""ORM mappings for the Focus To-Do export schema (see ``schema.sql``).

The tables are owned by the baseline migration's raw DDL, so these classes are
used for queries only and must mirror ``schema.sql`` column for column
(``tests/test_migration.py`` enforces this). Ids are opaque TEXT and are never
parsed as UUIDs, because the extension stores them in mixed case.
"""
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, SmallInteger, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


def _timestamptz() -> Mapped[datetime | None]:
    return mapped_column(DateTime(timezone=True), nullable=True)


def _flag() -> Mapped[bool]:
    return mapped_column(Boolean, nullable=False, server_default="false")


class ProjectRow(Base):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False, server_default="")
    obj_type: Mapped[str | None] = mapped_column(Text)
    parent_id: Mapped[str | None] = mapped_column(
        Text,
        ForeignKey("projects.id", ondelete="SET NULL", deferrable=True, initially="DEFERRED"),
        index=True,
    )
    color: Mapped[str | None] = mapped_column(Text)
    image_name: Mapped[str | None] = mapped_column(Text)
    is_default: Mapped[bool] = _flag()
    expanded: Mapped[bool] = _flag()
    ordering_rule: Mapped[int | None] = mapped_column(SmallInteger)
    type: Mapped[int | None] = mapped_column(Integer)
    sort_order: Mapped[int | None] = mapped_column(Integer)
    state: Mapped[int | None] = mapped_column(SmallInteger)
    sync: Mapped[int | None] = mapped_column(SmallInteger)
    creation_date: Mapped[datetime | None] = _timestamptz()


class TaskRow(Base):
    __tablename__ = "tasks"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    project_id: Mapped[str | None] = mapped_column(
        Text, ForeignKey("projects.id", ondelete="SET NULL"), index=True
    )
    name: Mapped[str] = mapped_column(Text, nullable=False, server_default="")
    obj_type: Mapped[str | None] = mapped_column(Text)
    remark: Mapped[str | None] = mapped_column(Text)
    tags: Mapped[str | None] = mapped_column(Text)
    priority: Mapped[int | None] = mapped_column(SmallInteger)
    sort_order: Mapped[int | None] = mapped_column(Integer)
    state: Mapped[int | None] = mapped_column(SmallInteger)
    sync: Mapped[int | None] = mapped_column(SmallInteger)
    is_finished: Mapped[bool] = _flag()
    is_expanded: Mapped[bool] = _flag()
    has_subtask: Mapped[bool] = _flag()
    estimate_pomo_num: Mapped[int | None] = mapped_column(Integer)
    actual_pomo_num: Mapped[int | None] = mapped_column(Integer)
    pomodoro_interval: Mapped[int | None] = mapped_column(Integer)
    creation_date: Mapped[datetime | None] = _timestamptz()
    deadline: Mapped[datetime | None] = _timestamptz()
    finished_date: Mapped[datetime | None] = _timestamptz()
    reminder_date: Mapped[datetime | None] = _timestamptz()
    reminders: Mapped[str | None] = mapped_column(Text)
    r_id: Mapped[str | None] = mapped_column(Text)
    r_cycle: Mapped[int | None] = mapped_column(SmallInteger)
    r_unit: Mapped[str | None] = mapped_column(Text)
    r_value: Mapped[str | None] = mapped_column(Text)
    r_first_deadline: Mapped[datetime | None] = _timestamptz()
    r_start_date: Mapped[datetime | None] = _timestamptz()
    r_end_date: Mapped[datetime | None] = _timestamptz()


class SubtaskRow(Base):
    __tablename__ = "subtasks"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    task_id: Mapped[str | None] = mapped_column(
        Text, ForeignKey("tasks.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(Text, nullable=False, server_default="")
    obj_type: Mapped[str | None] = mapped_column(Text)
    is_finished: Mapped[bool] = _flag()
    estimated_pomo_num: Mapped[int | None] = mapped_column(Integer)
    sort_order: Mapped[int | None] = mapped_column(Integer)
    state: Mapped[int | None] = mapped_column(SmallInteger)
    sync: Mapped[int | None] = mapped_column(SmallInteger)
    creation_date: Mapped[datetime | None] = _timestamptz()
    finished_date: Mapped[datetime | None] = _timestamptz()


class PomodoroSessionRow(Base):
    __tablename__ = "pomodoro_sessions"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    task_id: Mapped[str | None] = mapped_column(
        Text, ForeignKey("tasks.id", ondelete="SET NULL"), index=True
    )
    subtask_id: Mapped[str | None] = mapped_column(
        Text, ForeignKey("subtasks.id", ondelete="SET NULL"), index=True
    )
    obj_type: Mapped[str | None] = mapped_column(Text)
    interval_seconds: Mapped[int | None] = mapped_column(Integer)
    pomodoro_interval: Mapped[int | None] = mapped_column(Integer)
    is_manual: Mapped[bool] = _flag()
    state: Mapped[int | None] = mapped_column(SmallInteger)
    sync: Mapped[int | None] = mapped_column(SmallInteger)
    creation_date: Mapped[datetime | None] = _timestamptz()
    end_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)

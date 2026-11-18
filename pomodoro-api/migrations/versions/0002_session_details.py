"""Add session_details side table for session kind and interruption data.

Revision ID: 0002_session_details
Revises: 0001_focus_todo_baseline
Create Date: 2026-11-17

Adds a side table so the CLI can record session kind (focus, short_break,
long_break) and interruption data without modifying the four Focus To-Do
tables.  This keeps the one-time Focus To-Do import schema intact.
"""
from typing import Sequence, Union

from alembic import op

revision: str = "0002_session_details"
down_revision: Union[str, Sequence[str], None] = "0001_focus_todo_baseline"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """CREATE TABLE session_details (
    session_id       TEXT PRIMARY KEY REFERENCES pomodoro_sessions (id) ON DELETE CASCADE,
    kind             TEXT NOT NULL CHECK (kind IN ('focus', 'short_break', 'long_break')),
    interrupted      BOOLEAN NOT NULL DEFAULT FALSE,
    interrupt_reason TEXT
)"""
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS session_details")

"""create pomodoro_sessions

Revision ID: 0001_pomodoro_sessions
Revises:
Create Date: 2026-03-25

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001_pomodoro_sessions"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "pomodoro_sessions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("duration_minutes", sa.Integer(), nullable=False),
        sa.Column("label", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_pomodoro_sessions_started_at",
        "pomodoro_sessions",
        ["started_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_pomodoro_sessions_started_at", table_name="pomodoro_sessions")
    op.drop_table("pomodoro_sessions")

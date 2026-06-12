"""Create initial database schema.

Revision ID: 0001
Revises:
Create Date: 2026-06-12
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "container_events",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("container_name", sa.Text(), nullable=False),
        sa.Column("container_id", sa.Text(), nullable=False),
        sa.Column("action", sa.Text(), nullable=False),
        sa.Column("exit_code", sa.Text(), nullable=True),
        sa.Column("log_file_path", sa.Text(), nullable=True),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "monitored_event_actions",
        sa.Column("action", sa.String(), nullable=False),
        sa.PrimaryKeyConstraint("action"),
    )


def downgrade() -> None:
    op.drop_table("monitored_event_actions")
    op.drop_table("container_events")

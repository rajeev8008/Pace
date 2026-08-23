"""link focus sessions to daily routines

Revision ID: 0010
Revises: 0009
"""

from alembic import op
import sqlalchemy as sa


revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("focus_sessions", sa.Column("daily_task_id", sa.Integer(), nullable=True))
    op.create_foreign_key("fk_focus_sessions_daily_task_id", "focus_sessions", "daily_tasks", ["daily_task_id"], ["id"], ondelete="SET NULL")
    op.create_index("ix_focus_sessions_daily_task_id", "focus_sessions", ["daily_task_id"])


def downgrade() -> None:
    op.drop_index("ix_focus_sessions_daily_task_id", table_name="focus_sessions")
    op.drop_constraint("fk_focus_sessions_daily_task_id", "focus_sessions", type_="foreignkey")
    op.drop_column("focus_sessions", "daily_task_id")

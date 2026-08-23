"""Add focus sessions with one active timer."""

from alembic import op
import sqlalchemy as sa


revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "focus_sessions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("category", sa.String(100)),
        sa.Column("task_id", sa.Integer(), sa.ForeignKey("tasks.id", ondelete="SET NULL")),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True)),
        sa.Column("duration_seconds", sa.Integer()),
        sa.Column("notes", sa.Text()),
        sa.Column("active_slot", sa.Boolean(), nullable=True, server_default="true"),
        sa.CheckConstraint("duration_seconds IS NULL OR duration_seconds >= 0", name="focus_duration_nonnegative"),
        sa.CheckConstraint("ended_at IS NULL OR ended_at >= started_at", name="focus_time_order"),
        sa.CheckConstraint("(ended_at IS NULL) = (duration_seconds IS NULL)", name="focus_completion_state"),
        sa.CheckConstraint("active_slot IS NULL OR active_slot = true", name="focus_active_slot_value"),
        sa.UniqueConstraint("active_slot", name="one_active_focus_session"),
    )
    op.create_index("ix_focus_sessions_task_id", "focus_sessions", ["task_id"])
    op.create_index("ix_focus_sessions_started_at", "focus_sessions", ["started_at"])


def downgrade() -> None:
    op.drop_index("ix_focus_sessions_started_at", table_name="focus_sessions")
    op.drop_index("ix_focus_sessions_task_id", table_name="focus_sessions")
    op.drop_table("focus_sessions")

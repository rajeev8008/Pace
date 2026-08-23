"""Add recurring daily tasks and completion history."""

from alembic import op
import sqlalchemy as sa


revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table("daily_tasks", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("title", sa.String(200), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_table("daily_task_completions", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("daily_task_id", sa.Integer(), sa.ForeignKey("daily_tasks.id", ondelete="CASCADE"), nullable=False), sa.Column("completed_on", sa.Date(), nullable=False), sa.Column("completed_at", sa.DateTime(timezone=True), nullable=False), sa.UniqueConstraint("daily_task_id", "completed_on", name="daily_task_once_per_day"))


def downgrade() -> None:
    op.drop_table("daily_task_completions")
    op.drop_table("daily_tasks")

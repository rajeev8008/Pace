"""Add scheduling state and job tracking."""

from alembic import op
import sqlalchemy as sa


revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("tasks", sa.Column("reminder_processed_at", sa.DateTime(timezone=True)))
    op.add_column("preferences", sa.Column("next_daily_digest_at", sa.DateTime(timezone=True)))
    op.add_column("preferences", sa.Column("next_weekly_summary_at", sa.DateTime(timezone=True)))
    op.create_table(
        "jobs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("type", sa.String(14), nullable=False),
        sa.Column("status", sa.String(7), nullable=False, server_default="QUEUED"),
        sa.Column("occurrence_key", sa.String(200), nullable=False, unique=True),
        sa.Column("task_id", sa.Integer()),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True)),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("error", sa.Text()),
        sa.CheckConstraint(
            "type IN ('TASK_REMINDER', 'DAILY_DIGEST', 'WEEKLY_SUMMARY')",
            name="job_type",
        ),
        sa.CheckConstraint(
            "status IN ('QUEUED', 'RUNNING', 'SUCCESS', 'FAILED')",
            name="job_status",
        ),
        sa.CheckConstraint("attempts BETWEEN 0 AND 3", name="job_attempts"),
    )


def downgrade() -> None:
    op.drop_table("jobs")
    op.drop_column("preferences", "next_weekly_summary_at")
    op.drop_column("preferences", "next_daily_digest_at")
    op.drop_column("tasks", "reminder_processed_at")

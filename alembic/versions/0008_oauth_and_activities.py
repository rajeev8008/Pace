"""Add OAuth identities and the editable activity timeline."""

from alembic import op
import sqlalchemy as sa


revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("users", "password_hash", nullable=True)
    op.add_column("users", sa.Column("github_id", sa.String(64)))
    op.add_column("users", sa.Column("google_id", sa.String(255)))
    op.create_unique_constraint("uq_users_github_id", "users", ["github_id"])
    op.create_unique_constraint("uq_users_google_id", "users", ["google_id"])
    op.create_table(
        "activities",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("type", sa.String(20), nullable=False),
        sa.Column("source_type", sa.String(30)),
        sa.Column("source_id", sa.Integer()),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("detail", sa.Text()),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("type IN ('TASK', 'ROUTINE', 'FOCUS', 'GITHUB')", name="activity_type"),
        sa.UniqueConstraint("source_type", "source_id", name="activity_source_once"),
    )
    op.create_index("ix_activities_type", "activities", ["type"])
    op.create_index("ix_activities_occurred_at", "activities", ["occurred_at"])
    op.execute("INSERT INTO activities (type, source_type, source_id, title, detail, occurred_at) SELECT 'TASK', 'task', id, title, 'Scheduled task completed', completed_at FROM tasks WHERE completed_at IS NOT NULL")
    op.execute("INSERT INTO activities (type, source_type, source_id, title, detail, occurred_at) SELECT 'ROUTINE', 'daily_completion', c.id, t.title, 'Daily routine completed', c.completed_at FROM daily_task_completions c JOIN daily_tasks t ON t.id = c.daily_task_id")
    op.execute("INSERT INTO activities (type, source_type, source_id, title, detail, occurred_at) SELECT 'FOCUS', 'focus', id, COALESCE(category, 'Focus session'), 'Focus session completed', ended_at FROM focus_sessions WHERE ended_at IS NOT NULL")


def downgrade() -> None:
    op.drop_table("activities")
    op.drop_constraint("uq_users_google_id", "users", type_="unique")
    op.drop_constraint("uq_users_github_id", "users", type_="unique")
    op.drop_column("users", "google_id")
    op.drop_column("users", "github_id")
    op.alter_column("users", "password_hash", nullable=False)

"""Create tasks table."""

from alembic import op
import sqlalchemy as sa


revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tasks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("status", sa.String(9), nullable=False, server_default="PENDING"),
        sa.Column("priority", sa.String(6), nullable=False, server_default="MEDIUM"),
        sa.Column("due_at", sa.DateTime(timezone=True)),
        sa.Column("reminder_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint("status IN ('PENDING', 'COMPLETED')", name="task_status"),
        sa.CheckConstraint("priority IN ('LOW', 'MEDIUM', 'HIGH')", name="task_priority"),
    )


def downgrade() -> None:
    op.drop_table("tasks")

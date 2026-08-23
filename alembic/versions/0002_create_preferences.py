"""Create preferences table."""

from alembic import op
import sqlalchemy as sa


revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "preferences",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(320)),
        sa.Column("timezone", sa.String(64), nullable=False, server_default="Asia/Kolkata"),
        sa.Column("daily_digest_enabled", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("daily_digest_time", sa.Time(), nullable=False, server_default="20:00:00"),
        sa.Column("weekly_summary_enabled", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("weekly_summary_day", sa.String(9), nullable=False, server_default="SUNDAY"),
        sa.Column("weekly_summary_time", sa.Time(), nullable=False, server_default="20:00:00"),
        sa.CheckConstraint("id = 1", name="single_preferences_row"),
        sa.CheckConstraint(
            "weekly_summary_day IN ('MONDAY', 'TUESDAY', 'WEDNESDAY', 'THURSDAY', 'FRIDAY', 'SATURDAY', 'SUNDAY')",
            name="weekday",
        ),
    )


def downgrade() -> None:
    op.drop_table("preferences")

"""Add GitHub and LeetCode profile connections."""

from alembic import op
import sqlalchemy as sa

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("activity_type", "activities", type_="check")
    op.create_check_constraint("activity_type", "activities", "type IN ('TASK', 'ROUTINE', 'FOCUS', 'GITHUB', 'LEETCODE')")
    op.add_column("activities", sa.Column("external_id", sa.String(200)))
    op.create_unique_constraint("uq_activities_external_id", "activities", ["external_id"])
    op.create_table(
        "external_profiles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("provider", sa.String(20), nullable=False),
        sa.Column("username", sa.String(100), nullable=False),
        sa.Column("profile_url", sa.String(500), nullable=False),
        sa.Column("last_synced_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint("provider IN ('GITHUB', 'LEETCODE')", name="profile_provider"),
        sa.UniqueConstraint("provider", name="one_profile_per_provider"),
    )


def downgrade() -> None:
    op.drop_table("external_profiles")
    op.drop_constraint("uq_activities_external_id", "activities", type_="unique")
    op.drop_column("activities", "external_id")
    op.drop_constraint("activity_type", "activities", type_="check")
    op.create_check_constraint("activity_type", "activities", "type IN ('TASK', 'ROUTINE', 'FOCUS', 'GITHUB')")

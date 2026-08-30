"""Give every Pace account isolated application data."""

from alembic import op
import sqlalchemy as sa


revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


OWNED_TABLES = ("tasks", "preferences", "jobs", "daily_tasks", "focus_sessions", "activities", "external_profiles")


def upgrade() -> None:
    op.drop_constraint("single_user_account", "users", type_="check")
    op.execute("SELECT setval(pg_get_serial_sequence('users', 'id'), COALESCE(MAX(id), 1), true) FROM users")
    op.drop_constraint("single_preferences_row", "preferences", type_="check")
    op.execute("SELECT setval(pg_get_serial_sequence('preferences', 'id'), COALESCE(MAX(id), 1), true) FROM preferences")
    op.drop_constraint("one_active_focus_session", "focus_sessions", type_="unique")
    op.drop_constraint("activity_source_once", "activities", type_="unique")
    op.drop_constraint("uq_activities_external_id", "activities", type_="unique")
    op.drop_constraint("one_profile_per_provider", "external_profiles", type_="unique")
    op.drop_constraint("jobs_occurrence_key_key", "jobs", type_="unique")

    for table in OWNED_TABLES:
        op.add_column(table, sa.Column("user_id", sa.Integer(), nullable=True))
        op.execute(f"UPDATE {table} SET user_id = 1")
        op.alter_column(table, "user_id", nullable=False)
        op.create_foreign_key(f"fk_{table}_user_id", table, "users", ["user_id"], ["id"], ondelete="CASCADE")
        op.create_index(f"ix_{table}_user_id", table, ["user_id"])

    op.create_unique_constraint("uq_preferences_user_id", "preferences", ["user_id"])
    op.create_unique_constraint("job_occurrence_once_per_user", "jobs", ["user_id", "occurrence_key"])
    op.create_unique_constraint("one_active_focus_session_per_user", "focus_sessions", ["user_id", "active_slot"])
    op.create_unique_constraint("activity_source_once_per_user", "activities", ["user_id", "source_type", "source_id"])
    op.create_unique_constraint("activity_external_once_per_user", "activities", ["user_id", "external_id"])
    op.create_unique_constraint("one_profile_per_provider_per_user", "external_profiles", ["user_id", "provider"])


def downgrade() -> None:
    op.drop_constraint("one_profile_per_provider_per_user", "external_profiles", type_="unique")
    op.drop_constraint("activity_external_once_per_user", "activities", type_="unique")
    op.drop_constraint("activity_source_once_per_user", "activities", type_="unique")
    op.drop_constraint("one_active_focus_session_per_user", "focus_sessions", type_="unique")
    op.drop_constraint("job_occurrence_once_per_user", "jobs", type_="unique")
    op.drop_constraint("uq_preferences_user_id", "preferences", type_="unique")
    for table in reversed(OWNED_TABLES):
        op.drop_index(f"ix_{table}_user_id", table_name=table)
        op.drop_constraint(f"fk_{table}_user_id", table, type_="foreignkey")
        op.drop_column(table, "user_id")
    op.create_unique_constraint("one_profile_per_provider", "external_profiles", ["provider"])
    op.create_unique_constraint("uq_activities_external_id", "activities", ["external_id"])
    op.create_unique_constraint("activity_source_once", "activities", ["source_type", "source_id"])
    op.create_unique_constraint("one_active_focus_session", "focus_sessions", ["active_slot"])
    op.create_unique_constraint("jobs_occurrence_key_key", "jobs", ["occurrence_key"])
    op.create_check_constraint("single_preferences_row", "preferences", "id = 1")
    op.create_check_constraint("single_user_account", "users", "id = 1")

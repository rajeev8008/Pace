"""Use each account's verified email for summaries."""

from alembic import op


revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("UPDATE preferences SET email = users.email FROM users WHERE preferences.user_id = users.id AND preferences.email IS NULL")


def downgrade() -> None:
    pass

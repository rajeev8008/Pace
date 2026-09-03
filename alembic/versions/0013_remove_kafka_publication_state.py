"""Remove Kafka publication state from jobs."""

from alembic import op
import sqlalchemy as sa


revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_column("jobs", "published_at")


def downgrade() -> None:
    op.add_column("jobs", sa.Column("published_at", sa.DateTime(timezone=True)))

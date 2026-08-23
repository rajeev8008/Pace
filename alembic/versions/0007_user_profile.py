"""Store the single owner's email and display name."""

from alembic import op
import sqlalchemy as sa


revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("email", sa.String(320), nullable=True))
    op.add_column("users", sa.Column("display_name", sa.String(100), nullable=True))
    op.execute("UPDATE users SET display_name = username")
    op.execute("UPDATE users SET email = (SELECT email FROM preferences WHERE id = 1) WHERE email IS NULL")
    op.alter_column("users", "display_name", nullable=False)
    op.create_unique_constraint("uq_users_email", "users", ["email"])


def downgrade() -> None:
    op.drop_constraint("uq_users_email", "users", type_="unique")
    op.drop_column("users", "display_name")
    op.drop_column("users", "email")

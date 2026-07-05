"""enable pg_trgm and add contributor full_name trigram index

Revision ID: a2c0e5dc3468
Revises: cf8dae74a470
Create Date: 2026-07-05 17:05:57.062697

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a2c0e5dc3468"
down_revision: str | Sequence[str] | None = "cf8dae74a470"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.create_index(
        "ix_contributors_full_name_trgm",
        "contributors",
        ["full_name"],
        unique=False,
        postgresql_using="gin",
        postgresql_ops={"full_name": "gin_trgm_ops"},
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_contributors_full_name_trgm", table_name="contributors")
    op.execute("DROP EXTENSION IF EXISTS pg_trgm")

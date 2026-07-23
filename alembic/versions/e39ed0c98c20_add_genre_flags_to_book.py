"""add genre flags to book

Revision ID: e39ed0c98c20
Revises: a76f77c4291d
Create Date: 2026-07-23 22:11:32.421907

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e39ed0c98c20"
down_revision: str | Sequence[str] | None = "a76f77c4291d"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "book",
        sa.Column("genre_flags", sa.BigInteger(), server_default="0", nullable=False),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("book", "genre_flags")

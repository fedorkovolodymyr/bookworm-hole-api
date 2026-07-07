"""add email_verified_at to user

Revision ID: fe22d67a5546
Revises: 00562c775707
Create Date: 2026-07-07 17:12:40.683813

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "fe22d67a5546"
down_revision: str | Sequence[str] | None = "00562c775707"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "user",
        sa.Column("email_verified_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("user", "email_verified_at")

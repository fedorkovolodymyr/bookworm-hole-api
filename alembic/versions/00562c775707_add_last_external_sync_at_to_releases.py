"""add last_external_sync_at to releases

Revision ID: 00562c775707
Revises: 8859de0dfcbe
Create Date: 2026-07-05 19:02:40.785909

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "00562c775707"
down_revision: str | Sequence[str] | None = "8859de0dfcbe"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "releases",
        sa.Column("last_external_sync_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("releases", "last_external_sync_at")

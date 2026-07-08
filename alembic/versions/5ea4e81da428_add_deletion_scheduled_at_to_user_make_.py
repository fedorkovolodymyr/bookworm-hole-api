"""add deletion_scheduled_at to user, make review user_id nullable

Revision ID: 5ea4e81da428
Revises: 00562c775707
Create Date: 2026-07-08 12:36:06.923690

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "5ea4e81da428"
down_revision: str | Sequence[str] | None = "00562c775707"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.alter_column("review", "user_id", existing_type=sa.UUID(), nullable=True)
    op.add_column(
        "user",
        sa.Column("deletion_scheduled_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("user", "deletion_scheduled_at")
    op.alter_column("review", "user_id", existing_type=sa.UUID(), nullable=False)

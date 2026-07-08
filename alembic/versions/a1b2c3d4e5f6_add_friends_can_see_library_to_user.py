"""add friends_can_see_library to user

Revision ID: a1b2c3d4e5f6
Revises: 5d6d472bee49
Create Date: 2026-07-08 20:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: str | Sequence[str] | None = "5d6d472bee49"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "user",
        sa.Column(
            "friends_can_see_library",
            sa.Boolean(),
            nullable=False,
            server_default="true",
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("user", "friends_can_see_library")

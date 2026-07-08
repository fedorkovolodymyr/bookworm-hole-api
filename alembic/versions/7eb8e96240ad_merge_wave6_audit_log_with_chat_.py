"""merge wave6 audit log with chat migration

Revision ID: 7eb8e96240ad
Revises: a1f2b3c4d5e6, f3c1e4c34c28
Create Date: 2026-07-08 11:05:39.429612

"""

from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = "7eb8e96240ad"
down_revision: str | Sequence[str] | None = ("a1f2b3c4d5e6", "f3c1e4c34c28")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass

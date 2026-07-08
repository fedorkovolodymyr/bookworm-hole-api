"""merge wave1/wave2 migration heads

Revision ID: 6c90a3dd1750
Revises: fe22d67a5546, b1c2d3e4f5g6, 8500ecd54218
Create Date: 2026-07-07 22:45:27.061952

"""

from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = "6c90a3dd1750"
down_revision: str | Sequence[str] | None = (
    "fe22d67a5546",
    "b1c2d3e4f5g6",
    "8500ecd54218",
)
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass

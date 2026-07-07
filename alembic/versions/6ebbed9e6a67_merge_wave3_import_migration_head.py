"""merge wave3 import migration head

Revision ID: 6ebbed9e6a67
Revises: 6c90a3dd1750, bba0f93ce4e4
Create Date: 2026-07-07 23:35:01.251629

"""

from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = "6ebbed9e6a67"
down_revision: str | Sequence[str] | None = ("6c90a3dd1750", "bba0f93ce4e4")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass

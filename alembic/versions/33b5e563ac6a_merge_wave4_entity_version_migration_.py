"""merge wave4 entity_version migration head

Revision ID: 33b5e563ac6a
Revises: 6ebbed9e6a67, e1a9c2b7d4f0
Create Date: 2026-07-08 07:32:08.850025

"""

from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = "33b5e563ac6a"
down_revision: str | Sequence[str] | None = ("6ebbed9e6a67", "e1a9c2b7d4f0")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass

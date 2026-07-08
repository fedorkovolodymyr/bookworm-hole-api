"""merge wave5 chat migration with entity_version merge

Revision ID: f3c1e4c34c28
Revises: 33b5e563ac6a, d27a7afffe10
Create Date: 2026-07-08 09:46:26.616308

"""

from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = "f3c1e4c34c28"
down_revision: str | Sequence[str] | None = ("33b5e563ac6a", "d27a7afffe10")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass

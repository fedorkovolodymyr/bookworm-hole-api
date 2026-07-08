"""merge wave7 gdpr deletion with wave6 audit/chat

Revision ID: c2ad0667b645
Revises: 5ea4e81da428, 7eb8e96240ad
Create Date: 2026-07-08 13:11:15.605088

"""

from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = "c2ad0667b645"
down_revision: str | Sequence[str] | None = ("5ea4e81da428", "7eb8e96240ad")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass

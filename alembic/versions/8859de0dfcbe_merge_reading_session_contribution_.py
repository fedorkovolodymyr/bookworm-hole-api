"""merge reading_session, contribution, contributor_trgm heads

Revision ID: 8859de0dfcbe
Revises: 30290a645ea8, a2c0e5dc3468, b6e36fb94722
Create Date: 2026-07-05 18:17:16.551898

"""

# revision identifiers, used by Alembic.
revision: str = "8859de0dfcbe"
down_revision: tuple[str, ...] | None = (
    "30290a645ea8",
    "a2c0e5dc3468",
    "b6e36fb94722",
)
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass

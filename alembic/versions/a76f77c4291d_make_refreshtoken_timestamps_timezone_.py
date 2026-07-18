"""make refreshtoken timestamps timezone aware

Revision ID: a76f77c4291d
Revises: a1b2c3d4e5f6
Create Date: 2026-07-18 10:20:12.343352

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a76f77c4291d"
down_revision: str | Sequence[str] | None = "a1b2c3d4e5f6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "refreshtoken",
        "expires_at",
        existing_type=sa.TIMESTAMP(),
        type_=sa.DateTime(timezone=True),
        existing_nullable=False,
    )
    op.alter_column(
        "refreshtoken",
        "revoked_at",
        existing_type=sa.TIMESTAMP(),
        type_=sa.DateTime(timezone=True),
        existing_nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "refreshtoken",
        "revoked_at",
        existing_type=sa.DateTime(timezone=True),
        type_=sa.TIMESTAMP(),
        existing_nullable=True,
    )
    op.alter_column(
        "refreshtoken",
        "expires_at",
        existing_type=sa.DateTime(timezone=True),
        type_=sa.TIMESTAMP(),
        existing_nullable=False,
    )

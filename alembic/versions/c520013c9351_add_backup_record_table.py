"""add backup record table

Revision ID: c520013c9351
Revises: c2ad0667b645
Create Date: 2026-07-08 14:13:58.572392

"""

from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c520013c9351"
down_revision: str | Sequence[str] | None = "c2ad0667b645"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "backuprecord",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("drive_file_id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("filename", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_backuprecord_created_at"), "backuprecord", ["created_at"], unique=False
    )
    op.create_index(
        op.f("ix_backuprecord_user_id"), "backuprecord", ["user_id"], unique=False
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_backuprecord_user_id"), table_name="backuprecord")
    op.drop_index(op.f("ix_backuprecord_created_at"), table_name="backuprecord")
    op.drop_table("backuprecord")

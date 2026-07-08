"""add entity version table

Revision ID: e1a9c2b7d4f0
Revises: 00562c775707
Create Date: 2026-07-08 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e1a9c2b7d4f0"
down_revision: str | Sequence[str] | None = "00562c775707"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "entity_versions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "entity_type",
            sa.Enum("book", "release", "contributor", name="entitytype"),
            nullable=False,
        ),
        sa.Column("entity_id", sa.Uuid(), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("changed_by_user_id", sa.Uuid(), nullable=True),
        sa.Column(
            "change_source",
            sa.Enum(
                "admin", "contribution", "external_sync", "system", name="changesource"
            ),
            nullable=False,
        ),
        sa.Column("contribution_id", sa.Uuid(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["contribution_id"],
            ["contribution.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_entity_versions_changed_by_user_id"),
        "entity_versions",
        ["changed_by_user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_entity_versions_contribution_id"),
        "entity_versions",
        ["contribution_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_entity_versions_created_at"),
        "entity_versions",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_entity_versions_entity_id"),
        "entity_versions",
        ["entity_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_entity_versions_entity_type"),
        "entity_versions",
        ["entity_type"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_entity_versions_entity_type"), table_name="entity_versions")
    op.drop_index(op.f("ix_entity_versions_entity_id"), table_name="entity_versions")
    op.drop_index(op.f("ix_entity_versions_created_at"), table_name="entity_versions")
    op.drop_index(
        op.f("ix_entity_versions_contribution_id"), table_name="entity_versions"
    )
    op.drop_index(
        op.f("ix_entity_versions_changed_by_user_id"), table_name="entity_versions"
    )
    op.drop_table("entity_versions")
    sa.Enum(name="changesource").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="entitytype").drop(op.get_bind(), checkfirst=True)

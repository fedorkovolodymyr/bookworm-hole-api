"""add contribution table

Revision ID: b6e36fb94722
Revises: cf8dae74a470
Create Date: 2026-07-05 17:01:16.391770

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b6e36fb94722"
down_revision: str | Sequence[str] | None = "cf8dae74a470"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "contribution",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column(
            "kind",
            sa.Enum(
                "new_book",
                "new_release",
                "new_contributor",
                "edit_book",
                "edit_release",
                "edit_contributor",
                name="contributionkind",
            ),
            nullable=False,
        ),
        sa.Column("target_id", sa.Uuid(), nullable=True),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "draft",
                "submitted",
                "under_review",
                "approved",
                "rejected",
                "merged",
                name="contributionstatus",
            ),
            nullable=False,
        ),
        sa.Column("reviewer_id", sa.Uuid(), nullable=True),
        sa.Column("review_notes", sa.String(), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["reviewer_id"],
            ["user.id"],
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["user.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_contribution_created_at"), "contribution", ["created_at"], unique=False
    )
    op.create_index(
        op.f("ix_contribution_reviewer_id"),
        "contribution",
        ["reviewer_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_contribution_target_id"), "contribution", ["target_id"], unique=False
    )
    op.create_index(
        op.f("ix_contribution_user_id"), "contribution", ["user_id"], unique=False
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_contribution_user_id"), table_name="contribution")
    op.drop_index(op.f("ix_contribution_target_id"), table_name="contribution")
    op.drop_index(op.f("ix_contribution_reviewer_id"), table_name="contribution")
    op.drop_index(op.f("ix_contribution_created_at"), table_name="contribution")
    op.drop_table("contribution")
    sa.Enum(name="contributionstatus").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="contributionkind").drop(op.get_bind(), checkfirst=True)

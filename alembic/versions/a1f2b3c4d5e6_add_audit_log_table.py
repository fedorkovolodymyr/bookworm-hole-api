"""add audit log table

Revision ID: a1f2b3c4d5e6
Revises: 00562c775707
Create Date: 2026-07-08 09:55:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1f2b3c4d5e6"
down_revision: str | Sequence[str] | None = "00562c775707"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "auditlog",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("actor_id", sa.Uuid(), nullable=False),
        sa.Column(
            "action",
            sa.Enum(
                "approve_contribution",
                "reject_contribution",
                "claim_contribution",
                "activate_user",
                "deactivate_user",
                "promote_user",
                "demote_user",
                name="auditaction",
            ),
            nullable=False,
        ),
        sa.Column(
            "target_type",
            sa.Enum("contribution", "user", name="audittargettype"),
            nullable=False,
        ),
        sa.Column("target_id", sa.Uuid(), nullable=False),
        sa.Column(
            "audit_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.Column("ip_address", sa.String(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_auditlog_actor_id"), "auditlog", ["actor_id"], unique=False
    )
    op.create_index(
        op.f("ix_auditlog_target_id"), "auditlog", ["target_id"], unique=False
    )
    op.create_index(
        op.f("ix_auditlog_created_at"), "auditlog", ["created_at"], unique=False
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_auditlog_created_at"), table_name="auditlog")
    op.drop_index(op.f("ix_auditlog_target_id"), table_name="auditlog")
    op.drop_index(op.f("ix_auditlog_actor_id"), table_name="auditlog")
    op.drop_table("auditlog")
    sa.Enum(name="audittargettype").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="auditaction").drop(op.get_bind(), checkfirst=True)

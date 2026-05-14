"""companion account links

Revision ID: 20260510_0013
Revises: 20260510_0012
Create Date: 2026-05-10
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260510_0013"
down_revision: str | None = "20260510_0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "companion_account_links",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("companion_name", sa.Text(), nullable=False),
        sa.Column("companion_user_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["companion_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("owner_id", "companion_name", name="uq_companion_links_owner_name"),
    )
    op.create_index("ix_companion_links_owner", "companion_account_links", ["owner_id"])
    op.create_index(
        "ix_companion_links_companion_user",
        "companion_account_links",
        ["companion_user_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_companion_links_companion_user", table_name="companion_account_links")
    op.drop_index("ix_companion_links_owner", table_name="companion_account_links")
    op.drop_table("companion_account_links")

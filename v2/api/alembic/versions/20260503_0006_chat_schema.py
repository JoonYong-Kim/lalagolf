"""chat schema

Revision ID: 20260503_0006
Revises: 20260503_0005
Create Date: 2026-05-03
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260503_0006"
down_revision: str | None = "20260503_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def timestamp_columns() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        "llm_threads",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        *timestamp_columns(),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_llm_threads_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_llm_threads")),
    )
    op.create_index("ix_llm_threads_user_created_at", "llm_threads", ["user_id", "created_at"])

    op.create_table(
        "llm_messages",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("thread_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("role", sa.Text(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("evidence", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        *timestamp_columns(),
        sa.ForeignKeyConstraint(
            ["thread_id"],
            ["llm_threads.id"],
            name=op.f("fk_llm_messages_thread_id_llm_threads"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_llm_messages_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_llm_messages")),
    )
    op.create_index(
        "ix_llm_messages_thread_created_at",
        "llm_messages",
        ["thread_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_llm_messages_thread_created_at", table_name="llm_messages")
    op.drop_table("llm_messages")
    op.drop_index("ix_llm_threads_user_created_at", table_name="llm_threads")
    op.drop_table("llm_threads")

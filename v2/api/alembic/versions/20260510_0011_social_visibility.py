"""social visibility

Revision ID: 20260510_0011
Revises: 20260509_0010
Create Date: 2026-05-10
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260510_0011"
down_revision: str | None = "20260509_0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def timestamp_columns() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    ]


def upgrade() -> None:
    op.add_column("rounds", sa.Column("tee_off_time", sa.Text(), nullable=True))

    op.create_table(
        "follows",
        sa.Column("follower_id", sa.Uuid(), nullable=False),
        sa.Column("following_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("blocked_at", sa.DateTime(timezone=True), nullable=True),
        *timestamp_columns(),
        sa.CheckConstraint("status in ('pending', 'accepted', 'blocked')", name=op.f("ck_follows_status")),
        sa.ForeignKeyConstraint(
            ["follower_id"],
            ["users.id"],
            name=op.f("fk_follows_follower_id_users"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["following_id"],
            ["users.id"],
            name=op.f("fk_follows_following_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("follower_id", "following_id", name=op.f("pk_follows")),
    )

    op.create_table(
        "round_likes",
        sa.Column("round_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        *timestamp_columns(),
        sa.ForeignKeyConstraint(
            ["round_id"],
            ["rounds.id"],
            name=op.f("fk_round_likes_round_id_rounds"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_round_likes_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("round_id", "user_id", name=op.f("pk_round_likes")),
    )

    op.create_table(
        "round_comments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("round_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("parent_comment_id", sa.Uuid(), nullable=True),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        *timestamp_columns(),
        sa.CheckConstraint("status in ('active', 'deleted', 'hidden')", name=op.f("ck_round_comments_status")),
        sa.ForeignKeyConstraint(
            ["round_id"],
            ["rounds.id"],
            name=op.f("fk_round_comments_round_id_rounds"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_round_comments_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["parent_comment_id"],
            ["round_comments.id"],
            name=op.f("fk_round_comments_parent_comment_id_round_comments"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_round_comments")),
    )
    op.create_index(
        "ix_round_comments_round_created_at",
        "round_comments",
        ["round_id", "created_at"],
    )
    op.create_index(
        "ix_round_comments_user_created_at",
        "round_comments",
        ["user_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_round_comments_user_created_at", table_name="round_comments")
    op.drop_index("ix_round_comments_round_created_at", table_name="round_comments")
    op.drop_table("round_comments")
    op.drop_table("round_likes")
    op.drop_table("follows")
    op.drop_column("rounds", "tee_off_time")

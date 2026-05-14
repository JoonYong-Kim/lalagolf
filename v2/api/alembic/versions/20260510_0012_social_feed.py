"""social feed visibility fields

Revision ID: 20260510_0012
Revises: 20260510_0011
Create Date: 2026-05-10
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260510_0012"
down_revision: str | None = "20260510_0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "rounds",
        sa.Column("social_published_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_rounds_visibility_social_published",
        "rounds",
        ["visibility", "social_published_at", "id"],
    )
    op.execute(
        """
        UPDATE rounds
        SET social_published_at = updated_at
        WHERE visibility IN ('public', 'followers')
          AND social_published_at IS NULL
        """
    )

    op.add_column(
        "practice_diary_entries",
        sa.Column(
            "visibility",
            sa.Text(),
            nullable=False,
            server_default="private",
        ),
    )
    op.add_column(
        "practice_diary_entries",
        sa.Column("social_published_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_practice_diary_visibility_published",
        "practice_diary_entries",
        ["visibility", "social_published_at", "id"],
    )

    op.add_column(
        "round_goals",
        sa.Column(
            "visibility",
            sa.Text(),
            nullable=False,
            server_default="private",
        ),
    )
    op.add_column(
        "round_goals",
        sa.Column("social_published_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_round_goals_visibility_published",
        "round_goals",
        ["visibility", "social_published_at", "id"],
    )


def downgrade() -> None:
    op.drop_index("ix_round_goals_visibility_published", table_name="round_goals")
    op.drop_column("round_goals", "social_published_at")
    op.drop_column("round_goals", "visibility")
    op.drop_index(
        "ix_practice_diary_visibility_published",
        table_name="practice_diary_entries",
    )
    op.drop_column("practice_diary_entries", "social_published_at")
    op.drop_column("practice_diary_entries", "visibility")
    op.drop_index("ix_rounds_visibility_social_published", table_name="rounds")
    op.drop_column("rounds", "social_published_at")

"""round draft status and user club bag

Revision ID: 20260509_0010
Revises: 20260509_0009
Create Date: 2026-05-09
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260509_0010"
down_revision: str | None = "20260509_0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint("computed_status", "rounds", type_="check")
    op.create_check_constraint(
        "computed_status",
        "rounds",
        "computed_status in ('draft', 'pending', 'ready', 'stale', 'failed')",
    )

    op.add_column(
        "user_profiles",
        sa.Column(
            "club_bag",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("user_profiles", "club_bag")
    op.drop_constraint("computed_status", "rounds", type_="check")
    op.create_check_constraint(
        "computed_status",
        "rounds",
        "computed_status in ('pending', 'ready', 'stale', 'failed')",
    )

"""store session ip address as text

Revision ID: 20260503_0004
Revises: 20260503_0003
Create Date: 2026-05-03
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260503_0004"
down_revision: str | None = "20260503_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "user_sessions",
        "ip_address",
        existing_type=sa.Text(),
        type_=sa.Text(),
        postgresql_using="ip_address::text",
    )


def downgrade() -> None:
    op.alter_column(
        "user_sessions",
        "ip_address",
        existing_type=sa.Text(),
        type_=postgresql.INET(),
        postgresql_using="ip_address::inet",
    )

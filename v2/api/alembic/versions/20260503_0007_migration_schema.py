"""migration schema

Revision ID: 20260503_0007
Revises: 20260503_0006
Create Date: 2026-05-03
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260503_0007"
down_revision: str | None = "20260503_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def timestamp_columns() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        "migration_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("label", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("summary", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        *timestamp_columns(),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_migration_runs_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_migration_runs")),
    )
    op.create_index(
        "ix_migration_runs_user_created_at",
        "migration_runs",
        ["user_id", "created_at"],
    )

    op.create_table(
        "migration_id_map",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("migration_run_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("entity_type", sa.Text(), nullable=False),
        sa.Column("v1_id", sa.Text(), nullable=False),
        sa.Column("v2_id", sa.Uuid(), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        *timestamp_columns(),
        sa.ForeignKeyConstraint(
            ["migration_run_id"],
            ["migration_runs.id"],
            name=op.f("fk_migration_id_map_migration_run_id_migration_runs"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_migration_id_map_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_migration_id_map")),
        sa.UniqueConstraint(
            "migration_run_id",
            "entity_type",
            "v1_id",
            name="uq_migration_id_map_v1",
        ),
    )
    op.create_index(
        "ix_migration_id_map_run_entity",
        "migration_id_map",
        ["migration_run_id", "entity_type"],
    )

    op.create_table(
        "migration_issues",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("migration_run_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("severity", sa.Text(), nullable=False),
        sa.Column("code", sa.Text(), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        *timestamp_columns(),
        sa.ForeignKeyConstraint(
            ["migration_run_id"],
            ["migration_runs.id"],
            name=op.f("fk_migration_issues_migration_run_id_migration_runs"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_migration_issues_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_migration_issues")),
    )
    op.create_index(
        "ix_migration_issues_run_severity",
        "migration_issues",
        ["migration_run_id", "severity"],
    )


def downgrade() -> None:
    op.drop_index("ix_migration_issues_run_severity", table_name="migration_issues")
    op.drop_table("migration_issues")
    op.drop_index("ix_migration_id_map_run_entity", table_name="migration_id_map")
    op.drop_table("migration_id_map")
    op.drop_index("ix_migration_runs_user_created_at", table_name="migration_runs")
    op.drop_table("migration_runs")

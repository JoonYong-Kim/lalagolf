"""analysis schema

Revision ID: 20260503_0003
Revises: 20260502_0002
Create Date: 2026-05-03
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260503_0003"
down_revision: str | None = "20260502_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def timestamp_columns() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    ]


def user_fk(column_name: str = "user_id") -> sa.Column:
    return sa.Column(column_name, sa.Uuid(), nullable=False)


def upgrade() -> None:
    op.create_table(
        "round_metrics",
        sa.Column("id", sa.Uuid(), nullable=False),
        user_fk(),
        sa.Column("round_id", sa.Uuid(), nullable=False),
        sa.Column("category", sa.Text(), nullable=False),
        sa.Column("metric_key", sa.Text(), nullable=False),
        sa.Column("value", sa.Float(), nullable=True),
        sa.Column("sample_count", sa.Integer(), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        *timestamp_columns(),
        sa.ForeignKeyConstraint(
            ["round_id"],
            ["rounds.id"],
            name=op.f("fk_round_metrics_round_id_rounds"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_round_metrics_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_round_metrics")),
        sa.UniqueConstraint("round_id", "metric_key", name="uq_round_metrics_round_metric"),
    )
    op.create_index("ix_round_metrics_user_round", "round_metrics", ["user_id", "round_id"])
    op.create_index("ix_round_metrics_user_category", "round_metrics", ["user_id", "category"])

    op.create_table(
        "expected_score_tables",
        sa.Column("id", sa.Uuid(), nullable=False),
        user_fk(),
        sa.Column("scope_type", sa.Text(), nullable=False),
        sa.Column("scope_key", sa.Text(), nullable=False),
        sa.Column("sample_count", sa.Integer(), nullable=False),
        sa.Column("table_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        *timestamp_columns(),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_expected_score_tables_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_expected_score_tables")),
        sa.UniqueConstraint("user_id", "scope_type", "scope_key", name="uq_expected_tables_scope"),
    )
    op.create_index(
        "ix_expected_tables_user_scope",
        "expected_score_tables",
        ["user_id", "scope_type", "scope_key"],
    )

    op.create_table(
        "shot_values",
        sa.Column("id", sa.Uuid(), nullable=False),
        user_fk(),
        sa.Column("round_id", sa.Uuid(), nullable=False),
        sa.Column("hole_id", sa.Uuid(), nullable=False),
        sa.Column("shot_id", sa.Uuid(), nullable=False),
        sa.Column("category", sa.Text(), nullable=False),
        sa.Column("expected_before", sa.Float(), nullable=True),
        sa.Column("expected_after", sa.Float(), nullable=True),
        sa.Column("shot_cost", sa.Integer(), nullable=False),
        sa.Column("shot_value", sa.Float(), nullable=True),
        sa.Column("expected_lookup_level", sa.Text(), nullable=True),
        sa.Column("expected_sample_count", sa.Integer(), nullable=False),
        sa.Column("expected_source_scope", sa.Text(), nullable=True),
        sa.Column("expected_confidence", sa.Text(), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        *timestamp_columns(),
        sa.ForeignKeyConstraint(
            ["hole_id"],
            ["holes.id"],
            name=op.f("fk_shot_values_hole_id_holes"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["round_id"],
            ["rounds.id"],
            name=op.f("fk_shot_values_round_id_rounds"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["shot_id"],
            ["shots.id"],
            name=op.f("fk_shot_values_shot_id_shots"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_shot_values_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_shot_values")),
        sa.UniqueConstraint("shot_id", name="uq_shot_values_shot_id"),
    )
    op.create_index("ix_shot_values_user_round", "shot_values", ["user_id", "round_id"])
    op.create_index("ix_shot_values_user_category", "shot_values", ["user_id", "category"])

    op.create_table(
        "insights",
        sa.Column("id", sa.Uuid(), nullable=False),
        user_fk(),
        sa.Column("round_id", sa.Uuid(), nullable=True),
        sa.Column("scope_type", sa.Text(), nullable=False),
        sa.Column("scope_key", sa.Text(), nullable=False),
        sa.Column("category", sa.Text(), nullable=False),
        sa.Column("root_cause", sa.Text(), nullable=False),
        sa.Column("primary_evidence_metric", sa.Text(), nullable=False),
        sa.Column("dedupe_key", sa.Text(), nullable=False),
        sa.Column("problem", sa.Text(), nullable=False),
        sa.Column("evidence", sa.Text(), nullable=False),
        sa.Column("impact", sa.Text(), nullable=False),
        sa.Column("next_action", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Text(), nullable=False),
        sa.Column("priority_score", sa.Float(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("dismissed_at", sa.DateTime(timezone=True), nullable=True),
        *timestamp_columns(),
        sa.ForeignKeyConstraint(
            ["round_id"],
            ["rounds.id"],
            name=op.f("fk_insights_round_id_rounds"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_insights_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_insights")),
        sa.UniqueConstraint("user_id", "dedupe_key", name="uq_insights_user_dedupe"),
    )
    op.create_index(
        "ix_insights_user_status_priority",
        "insights",
        ["user_id", "status", "priority_score"],
    )
    op.create_index("ix_insights_user_category", "insights", ["user_id", "category"])

    op.create_table(
        "analysis_snapshots",
        sa.Column("id", sa.Uuid(), nullable=False),
        user_fk(),
        sa.Column("scope_type", sa.Text(), nullable=False),
        sa.Column("scope_key", sa.Text(), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        *timestamp_columns(),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_analysis_snapshots_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_analysis_snapshots")),
    )
    op.create_index(
        "ix_analysis_snapshots_user_scope",
        "analysis_snapshots",
        ["user_id", "scope_type", "scope_key"],
    )


def downgrade() -> None:
    op.drop_index("ix_analysis_snapshots_user_scope", table_name="analysis_snapshots")
    op.drop_table("analysis_snapshots")
    op.drop_index("ix_insights_user_category", table_name="insights")
    op.drop_index("ix_insights_user_status_priority", table_name="insights")
    op.drop_table("insights")
    op.drop_index("ix_shot_values_user_category", table_name="shot_values")
    op.drop_index("ix_shot_values_user_round", table_name="shot_values")
    op.drop_table("shot_values")
    op.drop_index("ix_expected_tables_user_scope", table_name="expected_score_tables")
    op.drop_table("expected_score_tables")
    op.drop_index("ix_round_metrics_user_category", table_name="round_metrics")
    op.drop_index("ix_round_metrics_user_round", table_name="round_metrics")
    op.drop_table("round_metrics")

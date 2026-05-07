"""practice and goals schema

Revision ID: 20260506_0008
Revises: 20260503_0007
Create Date: 2026-05-06
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260506_0008"
down_revision: str | None = "20260503_0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def timestamp_columns() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    ]


def upgrade() -> None:
    json_type = postgresql.JSONB(astext_type=sa.Text())

    op.create_table(
        "practice_plans",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("source_insight_id", sa.Uuid(), nullable=True),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("purpose", sa.Text(), nullable=True),
        sa.Column("category", sa.Text(), nullable=False),
        sa.Column("root_cause", sa.Text(), nullable=True),
        sa.Column("drill_json", json_type, nullable=False),
        sa.Column("target_json", json_type, nullable=False),
        sa.Column("scheduled_for", sa.Date(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        *timestamp_columns(),
        sa.ForeignKeyConstraint(
            ["source_insight_id"],
            ["insights.id"],
            name=op.f("fk_practice_plans_source_insight_id_insights"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_practice_plans_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_practice_plans")),
    )
    op.create_index(
        "ix_practice_plans_user_status_scheduled",
        "practice_plans",
        ["user_id", "status", "scheduled_for"],
    )
    op.create_index("ix_practice_plans_user_category", "practice_plans", ["user_id", "category"])
    op.create_index("ix_practice_plans_source_insight", "practice_plans", ["source_insight_id"])

    op.create_table(
        "practice_diary_entries",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("practice_plan_id", sa.Uuid(), nullable=True),
        sa.Column("source_insight_id", sa.Uuid(), nullable=True),
        sa.Column("round_id", sa.Uuid(), nullable=True),
        sa.Column("entry_date", sa.Date(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("category", sa.Text(), nullable=True),
        sa.Column("tags", json_type, nullable=False),
        sa.Column("confidence", sa.Text(), nullable=True),
        sa.Column("mood", sa.Text(), nullable=True),
        *timestamp_columns(),
        sa.ForeignKeyConstraint(
            ["practice_plan_id"],
            ["practice_plans.id"],
            name=op.f("fk_practice_diary_entries_practice_plan_id_practice_plans"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["round_id"],
            ["rounds.id"],
            name=op.f("fk_practice_diary_entries_round_id_rounds"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["source_insight_id"],
            ["insights.id"],
            name=op.f("fk_practice_diary_entries_source_insight_id_insights"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_practice_diary_entries_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_practice_diary_entries")),
    )
    op.create_index(
        "ix_practice_diary_user_entry_date",
        "practice_diary_entries",
        ["user_id", "entry_date"],
    )
    op.create_index(
        "ix_practice_diary_user_category",
        "practice_diary_entries",
        ["user_id", "category"],
    )
    op.create_index("ix_practice_diary_plan", "practice_diary_entries", ["practice_plan_id"])

    op.create_table(
        "round_goals",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("source_insight_id", sa.Uuid(), nullable=True),
        sa.Column("practice_plan_id", sa.Uuid(), nullable=True),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("category", sa.Text(), nullable=False),
        sa.Column("metric_key", sa.Text(), nullable=False),
        sa.Column("target_operator", sa.Text(), nullable=False),
        sa.Column("target_value", sa.Numeric(), nullable=True),
        sa.Column("target_value_max", sa.Numeric(), nullable=True),
        sa.Column("target_json", json_type, nullable=False),
        sa.Column("applies_to", sa.Text(), nullable=False),
        sa.Column("due_round_id", sa.Uuid(), nullable=True),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        *timestamp_columns(),
        sa.ForeignKeyConstraint(
            ["due_round_id"],
            ["rounds.id"],
            name=op.f("fk_round_goals_due_round_id_rounds"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["practice_plan_id"],
            ["practice_plans.id"],
            name=op.f("fk_round_goals_practice_plan_id_practice_plans"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["source_insight_id"],
            ["insights.id"],
            name=op.f("fk_round_goals_source_insight_id_insights"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_round_goals_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_round_goals")),
    )
    op.create_index(
        "ix_round_goals_user_status_due",
        "round_goals",
        ["user_id", "status", "due_date"],
    )
    op.create_index("ix_round_goals_user_category", "round_goals", ["user_id", "category"])
    op.create_index("ix_round_goals_source_insight", "round_goals", ["source_insight_id"])
    op.create_index("ix_round_goals_practice_plan", "round_goals", ["practice_plan_id"])

    op.create_table(
        "goal_evaluations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("goal_id", sa.Uuid(), nullable=False),
        sa.Column("round_id", sa.Uuid(), nullable=True),
        sa.Column("evaluation_status", sa.Text(), nullable=False),
        sa.Column("actual_value", sa.Numeric(), nullable=True),
        sa.Column("actual_json", json_type, nullable=False),
        sa.Column("evaluated_by", sa.Text(), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("evaluated_at", sa.DateTime(timezone=True), nullable=False),
        *timestamp_columns(),
        sa.ForeignKeyConstraint(
            ["goal_id"],
            ["round_goals.id"],
            name=op.f("fk_goal_evaluations_goal_id_round_goals"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["round_id"],
            ["rounds.id"],
            name=op.f("fk_goal_evaluations_round_id_rounds"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_goal_evaluations_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_goal_evaluations")),
    )
    op.create_index(
        "ix_goal_evaluations_user_evaluated",
        "goal_evaluations",
        ["user_id", "evaluated_at"],
    )
    op.create_index("ix_goal_evaluations_goal_round", "goal_evaluations", ["goal_id", "round_id"])
    op.create_index("ix_goal_evaluations_round", "goal_evaluations", ["round_id"])


def downgrade() -> None:
    op.drop_index("ix_goal_evaluations_round", table_name="goal_evaluations")
    op.drop_index("ix_goal_evaluations_goal_round", table_name="goal_evaluations")
    op.drop_index("ix_goal_evaluations_user_evaluated", table_name="goal_evaluations")
    op.drop_table("goal_evaluations")
    op.drop_index("ix_round_goals_practice_plan", table_name="round_goals")
    op.drop_index("ix_round_goals_source_insight", table_name="round_goals")
    op.drop_index("ix_round_goals_user_category", table_name="round_goals")
    op.drop_index("ix_round_goals_user_status_due", table_name="round_goals")
    op.drop_table("round_goals")
    op.drop_index("ix_practice_diary_plan", table_name="practice_diary_entries")
    op.drop_index("ix_practice_diary_user_category", table_name="practice_diary_entries")
    op.drop_index("ix_practice_diary_user_entry_date", table_name="practice_diary_entries")
    op.drop_table("practice_diary_entries")
    op.drop_index("ix_practice_plans_source_insight", table_name="practice_plans")
    op.drop_index("ix_practice_plans_user_category", table_name="practice_plans")
    op.drop_index("ix_practice_plans_user_status_scheduled", table_name="practice_plans")
    op.drop_table("practice_plans")

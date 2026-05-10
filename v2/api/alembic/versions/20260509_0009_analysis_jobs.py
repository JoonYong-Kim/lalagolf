"""analysis jobs

Revision ID: 20260509_0009
Revises: 20260506_0008
Create Date: 2026-05-09
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260509_0009"
down_revision: str | None = "20260506_0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def timestamp_columns() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        "analysis_jobs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("round_id", sa.Uuid(), nullable=False),
        sa.Column("kind", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("rq_job_id", sa.Text(), nullable=True),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        *timestamp_columns(),
        sa.CheckConstraint(
            "status in ('queued', 'running', 'succeeded', 'failed')",
            name=op.f("ck_analysis_jobs_analysis_job_status"),
        ),
        sa.ForeignKeyConstraint(
            ["round_id"],
            ["rounds.id"],
            name=op.f("fk_analysis_jobs_round_id_rounds"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_analysis_jobs_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_analysis_jobs")),
    )
    op.create_index(
        "ix_analysis_jobs_user_status_created",
        "analysis_jobs",
        ["user_id", "status", "created_at"],
    )
    op.create_index("ix_analysis_jobs_round_created", "analysis_jobs", ["round_id", "created_at"])
    op.create_index("ix_analysis_jobs_rq_job_id", "analysis_jobs", ["rq_job_id"])


def downgrade() -> None:
    op.drop_index("ix_analysis_jobs_rq_job_id", table_name="analysis_jobs")
    op.drop_index("ix_analysis_jobs_round_created", table_name="analysis_jobs")
    op.drop_index("ix_analysis_jobs_user_status_created", table_name="analysis_jobs")
    op.drop_table("analysis_jobs")
